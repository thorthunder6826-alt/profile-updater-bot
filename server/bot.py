import os
import logging
import asyncio
import re
import io
import json
import psycopg2
import psycopg2.extras
import httpx
from urllib.parse import quote
from typing import Dict, List, Optional
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, ContextTypes
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

DATABASE_URL = os.environ.get('DATABASE_URL', '')
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
HOST_USER_ID = int(os.environ.get('HOST_USER_ID', '0'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

netflix_sessions: Dict[int, dict] = {}

MAX_TG_MSG = 4000

async def safe_edit(msg, text: str, **kwargs):
    if len(text) > MAX_TG_MSG:
        text = text[:MAX_TG_MSG - 20] + "\n...(truncated)"
    try:
        await msg.edit_text(text, **kwargs)
    except Exception as e:
        logger.error(f"Failed to edit message: {e}")
        try:
            await msg.edit_text(text[:500])
        except:
            pass

async def safe_reply(message, text: str, **kwargs):
    if len(text) > MAX_TG_MSG:
        text = text[:MAX_TG_MSG - 20] + "\n...(truncated)"
    try:
        await message.reply_text(text, **kwargs)
    except Exception as e:
        logger.error(f"Failed to reply: {e}")

def short_error(e: Exception) -> str:
    s = str(e)
    if len(s) > 200:
        s = s[:200] + "..."
    return s

CHROME_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-extensions",
    "--disable-background-networking",
    "--disable-default-apps",
    "--disable-sync",
    "--no-first-run",
    "--disable-blink-features=AutomationControlled",
]

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"


def get_db():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS authorized_users (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL UNIQUE,
            added_by BIGINT,
            added_at TIMESTAMP DEFAULT NOW()
        )
    """)
    conn.commit()
    cur.close()
    conn.close()
    logger.info("Database initialized")


class NetflixBrowser:
    def __init__(self, cookies: str):
        self.raw_cookies = cookies
        self.cookies = self._parse_cookies_for_playwright(cookies)
        self.http_cookies = self._parse_cookies_for_http(cookies)
        self.profiles_cache: List[dict] = []
        self.build_id: Optional[str] = None

    def _parse_cookies_for_playwright(self, cookie_str: str) -> list:
        cookies = []
        for item in cookie_str.split(';'):
            item = item.strip()
            if '=' in item:
                key, value = item.split('=', 1)
                cookies.append({
                    "name": key.strip(),
                    "value": value.strip(),
                    "domain": ".netflix.com",
                    "path": "/"
                })
        return cookies

    def _parse_cookies_for_http(self, cookie_str: str) -> dict:
        cookies = {}
        for item in cookie_str.split(';'):
            item = item.strip()
            if '=' in item:
                key, value = item.split('=', 1)
                cookies[key.strip()] = value.strip()
        return cookies

    async def _launch_browser(self) -> tuple:
        p = await async_playwright().start()
        browser = await p.chromium.launch(
            headless=True,
            args=CHROME_ARGS
        )
        context = await browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1920, "height": 1080},
            locale="en-US"
        )
        await context.add_cookies(self.cookies)
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return p, browser, context

    async def _safe_close(self, p=None, browser=None):
        try:
            if browser:
                await browser.close()
        except:
            pass
        try:
            if p:
                await p.stop()
        except:
            pass

    @staticmethod
    async def login_with_credentials(email: str, password: str) -> tuple:
        p = None
        browser = None
        try:
            p = await async_playwright().start()
            browser = await p.chromium.launch(headless=True, args=CHROME_ARGS)
            context = await browser.new_context(
                user_agent=USER_AGENT,
                viewport={"width": 1280, "height": 900}
            )
            page = await context.new_page()

            await page.goto("https://www.netflix.com/login", wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)

            if "login" not in page.url.lower():
                await browser.close()
                await p.stop()
                return False, "Could not reach login page", ""

            email_input = page.locator("input[name='userLoginId']").first
            if await email_input.count() == 0:
                email_input = page.locator("input[type='email']").first
            if await email_input.count() == 0:
                await browser.close()
                await p.stop()
                return False, "Email input not found", ""

            await email_input.click()
            await page.keyboard.type(email, delay=30)
            await page.wait_for_timeout(500)

            continue_btn = page.locator("button[type='submit']").first
            if await continue_btn.count() > 0:
                await continue_btn.click()
                await page.wait_for_timeout(3000)

            pwd_input = page.locator("input[name='password'], input[type='password']").first
            for _ in range(5):
                if await pwd_input.count() > 0:
                    break
                await page.wait_for_timeout(1000)

            if await pwd_input.count() == 0:
                await browser.close()
                await p.stop()
                return False, "Password input not found", ""

            await pwd_input.click()
            await page.keyboard.type(password, delay=30)
            await page.wait_for_timeout(500)

            sign_in_btn = page.locator("button[type='submit']").first
            if await sign_in_btn.count() > 0:
                await sign_in_btn.click()
            else:
                await page.keyboard.press("Enter")

            await page.wait_for_timeout(6000)

            error_msg = page.locator("[data-uia='error-message-container'], .ui-message-contents, [data-uia='text']").first
            if await error_msg.count() > 0:
                error_text = await error_msg.text_content()
                if error_text and any(w in error_text.lower() for w in ["incorrect", "wrong", "invalid"]):
                    await browser.close()
                    await p.stop()
                    return False, f"Login failed: {error_text}", ""

            current_url = page.url.lower()
            if "login" in current_url and "browse" not in current_url and "profile" not in current_url:
                await page.wait_for_timeout(2000)
                current_url = page.url.lower()
                if "login" in current_url:
                    await browser.close()
                    await p.stop()
                    return False, "Login failed - check credentials", ""

            if "browse" in current_url or "profile" in current_url:
                cookies = await context.cookies()
                cookie_parts = []
                for cookie in cookies:
                    if cookie["name"] in ["NetflixId", "SecureNetflixId"]:
                        cookie_parts.append(f"{cookie['name']}={cookie['value']}")

                if len(cookie_parts) >= 2:
                    cookie_string = "; ".join(cookie_parts)
                    await browser.close()
                    await p.stop()
                    return True, "Login successful!", cookie_string
                else:
                    await browser.close()
                    await p.stop()
                    return False, "Could not extract session cookies", ""

            await browser.close()
            await p.stop()
            return False, f"Login failed - unexpected page: {page.url}", ""

        except Exception as e:
            if browser:
                try:
                    await browser.close()
                except:
                    pass
            if p:
                try:
                    await p.stop()
                except:
                    pass
            return False, f"Error: {str(e)}", ""

    async def validate_session(self) -> tuple:
        try:
            async with httpx.AsyncClient(
                cookies=self.http_cookies,
                headers={"User-Agent": USER_AGENT},
                follow_redirects=True,
                timeout=15.0
            ) as client:
                response = await client.get("https://www.netflix.com/browse")

                if "login" in str(response.url).lower() and "browse" not in str(response.url).lower():
                    return False, "Session expired"

                if response.status_code == 200 and ("profiles" in response.text.lower() or "browse" in str(response.url).lower()):
                    return True, "Session valid"

                return False, "Invalid session"
        except Exception as e:
            return False, f"Error: {str(e)}"

    async def _extract_build_id(self, content: str) -> Optional[str]:
        patterns = [
            r'"BUILD_IDENTIFIER"\s*:\s*"([^"]+)"',
            r'buildIdentifier"\s*:\s*"([^"]+)"',
            r'/nf/([a-f0-9]+)/',
        ]
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                self.build_id = match.group(1)
                return self.build_id
        return None

    async def get_profiles(self) -> tuple:
        try:
            async with httpx.AsyncClient(
                cookies=self.http_cookies,
                headers={"User-Agent": USER_AGENT},
                follow_redirects=True,
                timeout=15.0
            ) as client:
                response = await client.get("https://www.netflix.com/ManageProfiles")

                if "login" in str(response.url).lower():
                    return False, "Session expired"

                content = response.text
                await self._extract_build_id(content)

                profiles = []
                seen_guids = set()

                pattern1 = r'"guid"\s*:\s*"([^"]+)"[^}]*?"profileName"\s*:\s*"([^"]+)"'
                pattern2 = r'"([A-Z0-9]{20,})"\s*:\s*\{[^}]*"profileName"\s*:\s*"([^"]+)"'
                pattern3 = r'"profileName"\s*:\s*"([^"]+)"[^}]*?"guid"\s*:\s*"([^"]+)"'

                matches1 = re.findall(pattern1, content)
                for guid, name in matches1:
                    if guid not in seen_guids and len(guid) > 10:
                        seen_guids.add(guid)
                        try:
                            name = name.encode('latin-1').decode('unicode_escape')
                        except:
                            pass
                        profiles.append({
                            "guid": guid,
                            "profileName": name,
                            "isKids": False,
                            "isLocked": False
                        })

                if not profiles:
                    matches2 = re.findall(pattern2, content)
                    for guid, name in matches2:
                        if guid not in seen_guids:
                            seen_guids.add(guid)
                            try:
                                name = name.encode('latin-1').decode('unicode_escape')
                            except:
                                pass
                            profiles.append({
                                "guid": guid,
                                "profileName": name,
                                "isKids": False,
                                "isLocked": False
                            })

                if not profiles:
                    matches3 = re.findall(pattern3, content)
                    for name, guid in matches3:
                        if guid not in seen_guids and len(guid) > 10:
                            seen_guids.add(guid)
                            try:
                                name = name.encode('latin-1').decode('unicode_escape')
                            except:
                                pass
                            profiles.append({
                                "guid": guid,
                                "profileName": name,
                                "isKids": False,
                                "isLocked": False
                            })

                kids_pattern = r'"isKids"\s*:\s*true[^}]*"guid"\s*:\s*"([^"]+)"'
                kids_pattern2 = r'"guid"\s*:\s*"([^"]+)"[^}]*"isKids"\s*:\s*true'
                kids_guids = set()
                for pattern in [kids_pattern, kids_pattern2]:
                    for match in re.findall(pattern, content):
                        kids_guids.add(match)

                for profile in profiles:
                    if profile["guid"] in kids_guids:
                        profile["isKids"] = True

                self.profiles_cache = profiles
                logger.info(f"Found {len(profiles)} profiles")
                return True, {"profiles": profiles}

        except Exception as e:
            logger.error(f"Get profiles error: {e}")
            return False, f"Error: {str(e)}"

    async def _update_profile_on_page(self, page: Page, guid: str, new_name: str, password: str, index: int) -> dict:
        try:
            return await asyncio.wait_for(
                self._do_update_profile(page, guid, new_name, password, index),
                timeout=60.0
            )
        except asyncio.TimeoutError:
            logger.error(f"[{index}] Profile update timed out for {guid}")
            return {"index": index, "success": False, "error": "Timed out after 45s"}
        except Exception as e:
            logger.error(f"[{index}] Update profile error: {e}")
            return {"index": index, "success": False, "error": str(e)}

    async def _handle_mfa_if_needed(self, page: Page, password: str, target_url: str, index: int) -> bool:
        if "/mfa" not in page.url.lower():
            return True

        logger.info(f"[{index}] MFA page detected: {page.url}")

        confirm_clicked = False
        for t in range(60):
            pwd_input = page.locator("input[type='password']:visible").first
            if await pwd_input.count() > 0:
                await pwd_input.fill(password)
                logger.info(f"[{index}] MFA: entered password")

                for s in ["button:has-text('Submit')", "button[type='submit']", "button:has-text('Continue')"]:
                    btn = page.locator(s).first
                    if await btn.count() > 0 and await btn.is_visible():
                        await btn.click()
                        break

                for w in range(40):
                    await page.wait_for_timeout(250)
                    if "/mfa" not in page.url.lower():
                        logger.info(f"[{index}] MFA: passed -> {page.url}")
                        if target_url and target_url not in page.url:
                            logger.info(f"[{index}] MFA: redirecting to {target_url}")
                            await page.goto(target_url, wait_until="domcontentloaded", timeout=20000)
                        return True
                    wrong = await page.locator("text=Incorrect password").count() + \
                            await page.locator("text=Wrong password").count()
                    if wrong > 0:
                        logger.error(f"[{index}] MFA: incorrect password")
                        return False
                if "/mfa" not in page.url.lower():
                    if target_url and target_url not in page.url:
                        await page.goto(target_url, wait_until="domcontentloaded", timeout=20000)
                    return True
                return False

            if not confirm_clicked:
                confirm = page.locator("button:has-text('Confirm password')").first
                if await confirm.count() > 0:
                    await confirm.click()
                    confirm_clicked = True
                    logger.info(f"[{index}] MFA: clicked Confirm password")
                    await page.wait_for_timeout(2000)
                    continue

            err = await page.locator("text=Looks like something went wrong").count()
            if err > 0:
                logger.warning(f"[{index}] MFA: error page, navigating to target")
                await page.goto(target_url, wait_until="domcontentloaded", timeout=20000)
                if "/mfa" not in page.url.lower():
                    return True
                confirm_clicked = False

            await page.wait_for_timeout(500)

        logger.error(f"[{index}] MFA: timed out")
        return False

    async def _click_name_link(self, page: Page, old_name: str, index: int) -> bool:
        edit_selectors = [
            "a:has-text('Edit personal')",
            "a:has-text('personal and contact')",
            "a:has-text('Edit profile')",
        ]
        for selector in edit_selectors:
            try:
                el = page.locator(selector).first
                if await el.count() > 0 and await el.is_visible():
                    await el.click()
                    logger.info(f"[{index}] Clicked edit link: {selector}")
                    return True
            except:
                pass

        all_links = await page.locator("a:visible, button:visible, [role='button']:visible, [role='link']:visible").all()
        for link in all_links:
            text = ""
            href = ""
            try:
                text = (await link.inner_text()).strip()
                href = (await link.get_attribute("href")) or ""
            except:
                pass
            if "edit personal" in text.lower() or "personal and contact" in text.lower():
                await link.click()
                logger.info(f"[{index}] Clicked 'Edit personal' link")
                return True
            if old_name and text.strip() == old_name.strip() and "/settings/" in href:
                await link.click()
                logger.info(f"[{index}] Clicked exact name link: '{text}'")
                return True

        if old_name:
            for link in all_links:
                text = ""
                href = ""
                try:
                    text = (await link.inner_text()).strip()
                    href = (await link.get_attribute("href")) or ""
                except:
                    pass
                if old_name.lower() in text.lower() and len(text) < len(old_name) + 20:
                    if "/browse" not in href and "/profilesgate" not in href:
                        await link.click()
                        logger.info(f"[{index}] Clicked name-matching link: '{text}'")
                        return True

        return False

    async def _do_update_profile(self, page: Page, guid: str, new_name: str, password: str, index: int) -> dict:
        logger.info(f"[{index}] Updating profile: {guid} -> {new_name}")

        old_name = None
        for p in self.profiles_cache:
            if p.get("guid") == guid:
                old_name = p.get("profileName", "")
                break

        settings_url = f"https://www.netflix.com/settings/{guid}"

        on_settings = False
        for attempt in range(4):
            try:
                await page.goto(settings_url, wait_until="domcontentloaded", timeout=20000)
            except Exception as nav_err:
                if attempt < 3:
                    logger.warning(f"[{index}] Nav failed (attempt {attempt+1}), retrying...")
                    await page.wait_for_timeout(1000)
                    continue
                return {"index": index, "success": False, "error": f"Navigation failed: {short_error(nav_err)}"}

            if "login" in page.url.lower():
                return {"index": index, "success": False, "error": "Session expired"}

            if "/browse" in page.url.lower() or "/profilesgate" in page.url.lower():
                logger.warning(f"[{index}] Redirected to {page.url} (attempt {attempt+1}), retrying...")
                await page.wait_for_timeout(1500 * (attempt + 1))
                continue

            if "/mfa" in page.url.lower():
                mfa_ok = await self._handle_mfa_if_needed(page, password, settings_url, index)
                if not mfa_ok:
                    return {"index": index, "success": False, "error": "MFA verification failed"}

            if "/settings/" in page.url and "/mfa" not in page.url:
                on_settings = True
                break

        if not on_settings:
            logger.warning(f"[{index}] Could not reach settings page, falling back to recreate")
            return {"index": index, "success": False, "error": "MFA_BLOCKED", "needs_recreate": True}

        logger.info(f"[{index}] On settings page: {page.url}")

        clicked_name = await self._click_name_link(page, old_name, index)
        if not clicked_name:
            return {"index": index, "success": False, "error": "MFA_BLOCKED", "needs_recreate": True}

        if "/mfa" in page.url.lower():
            logger.info(f"[{index}] MFA triggered for profile edit - using delete+recreate fallback")
            return {"index": index, "success": False, "error": "MFA_BLOCKED", "needs_recreate": True}

        if "/browse" in page.url.lower():
            logger.warning(f"[{index}] Redirected to browse after clicking name, falling back to recreate")
            return {"index": index, "success": False, "error": "MFA_BLOCKED", "needs_recreate": True}

        name_input = None
        for attempt in range(25):
            name_input = await self._try_find_name_input(page, index)
            if name_input:
                break
            await page.wait_for_timeout(300)

        if name_input is None:
            logger.warning(f"[{index}] Name input not found on {page.url}, falling back to recreate")
            return {"index": index, "success": False, "error": "MFA_BLOCKED", "needs_recreate": True}

        logger.info(f"[{index}] Editing name to '{new_name}'")
        await name_input.click()
        await name_input.press("Control+a")
        await name_input.fill("")
        await name_input.type(new_name, delay=20)

        save_selectors = [
            "button:has-text('Save')",
            "button[data-uia='profile-save-button']",
            "button[type='submit']",
            "button:has-text('Done')",
        ]

        for selector in save_selectors:
            el = page.locator(selector).first
            if await el.count() > 0 and await el.is_visible():
                await el.click()
                logger.info(f"[{index}] Clicked save: {selector}")
                break

        for w in range(15):
            await page.wait_for_timeout(250)
            if "/settings" not in page.url.lower():
                break

        logger.info(f"[{index}] Profile updated: {new_name}")
        return {"index": index, "success": True, "new_name": new_name}

    async def _try_find_name_input(self, page: Page, index: int):
        selectors = [
            "input[data-uia='profile-name-entry']",
            "input#profile-name-entry",
            "input[name='profileName']",
            "input[name='profile-name']",
            "input[id*='profile-name']",
            "input[id*='profileName']",
            "input[class*='profile-name']",
            "input[class*='profileName']",
            "input[placeholder*='Name']",
            "input[aria-label*='Profile name' i]",
            "input[aria-label*='name' i]",
        ]
        for selector in selectors:
            try:
                el = page.locator(selector).first
                if await el.count() > 0 and await el.is_visible():
                    logger.info(f"[{index}] Found name input: {selector}")
                    return el
            except:
                pass

        visible_text_inputs = await page.locator("input[type='text']:visible, input:not([type]):visible").all()
        logger.info(f"[{index}] Visible text inputs on page: {len(visible_text_inputs)}")
        for i, inp in enumerate(visible_text_inputs):
            inp_type = await inp.get_attribute("type") or ""
            inp_name = await inp.get_attribute("name") or ""
            inp_id = await inp.get_attribute("id") or ""
            inp_val = ""
            try:
                inp_val = await inp.input_value()
            except:
                pass
            logger.info(f"[{index}] text input[{i}]: type={inp_type} name={inp_name} id={inp_id} value='{inp_val}'")
            if inp_type not in ["hidden", "password", "email", "search", "checkbox", "radio"]:
                if "search" not in inp_name.lower() and "search" not in inp_id.lower():
                    logger.info(f"[{index}] Using text input[{i}] as name input")
                    return inp

        return None

    async def _update_single_profile(self, guid: str, new_name: str, password: str, index: int) -> dict:
        p = None
        browser = None
        try:
            p, browser, context = await self._launch_browser()
            page = await context.new_page()
            result = await self._update_profile_on_page(page, guid, new_name, password, index)
            await self._safe_close(p, browser)
            return result
        except Exception as e:
            await self._safe_close(p, browser)
            return {"index": index, "success": False, "error": str(e)}

    async def _recreate_profile(self, guid: str, old_name: str, new_name: str, index: int) -> dict:
        logger.info(f"[{index}] Deleting profile '{old_name}' ({guid}) for recreate")
        del_ok, del_msg = await self.delete_profile(guid)
        if not del_ok:
            return {"index": index, "success": False, "error": f"Delete failed: {del_msg}"}
        logger.info(f"[{index}] Deleted, now adding '{new_name}'")
        await asyncio.sleep(0.5)
        add_result = await self._add_single_profile(new_name, index)
        if isinstance(add_result, dict) and add_result.get("success"):
            logger.info(f"[{index}] Recreated: {old_name} -> {new_name}")
            return {"index": index, "success": True, "new_name": new_name}
        error = add_result.get("error", "Failed") if isinstance(add_result, dict) else str(add_result)
        return {"index": index, "success": False, "error": f"Recreate failed: {error}"}

    async def _staggered_update(self, guid: str, new_name: str, password: str, index: int, delay: float) -> dict:
        if delay > 0:
            await asyncio.sleep(delay)
        return await self._update_single_profile(guid, new_name, password, index)

    async def update_all_profiles_parallel(self, profiles: List[dict], new_names: List[str], password: str) -> List[dict]:
        tasks = []
        for i, (profile, new_name) in enumerate(zip(profiles, new_names)):
            guid = profile.get("guid", "")
            if not guid:
                continue
            tasks.append(self._staggered_update(guid, new_name, password, i, delay=i * 0.8))

        if not tasks:
            return [{"index": i, "success": False, "error": "No GUID"} for i in range(len(profiles))]

        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        results = [None] * len(profiles)
        mfa_tasks = []
        for i, r in enumerate(raw_results):
            if isinstance(r, Exception):
                results[i] = {"index": i, "success": False, "error": str(r)}
            elif isinstance(r, dict) and r.get("needs_recreate"):
                profile = profiles[i]
                mfa_tasks.append((i, self._recreate_profile(
                    profile.get("guid", ""), profile.get("profileName", "Unknown"), new_names[i], i
                )))
                results[i] = r
            else:
                results[i] = r if isinstance(r, dict) else {"index": i, "success": False, "error": str(r)}

        if mfa_tasks:
            logger.info(f"Recreating {len(mfa_tasks)} MFA-blocked profiles in parallel...")
            recreate_results = await asyncio.gather(
                *[task for _, task in mfa_tasks], return_exceptions=True
            )
            for (idx, _), recreate_r in zip(mfa_tasks, recreate_results):
                if isinstance(recreate_r, Exception):
                    results[idx] = {"index": idx, "success": False, "error": str(recreate_r)}
                elif isinstance(recreate_r, dict):
                    results[idx] = recreate_r

        return results

    async def _set_pin_on_page(self, page: Page, guid: str, pin: str, password: str, index: int) -> dict:
        try:
            return await asyncio.wait_for(
                self._do_set_pin(page, guid, pin, password, index),
                timeout=90.0
            )
        except asyncio.TimeoutError:
            logger.error(f"[{index}] PIN set timed out for {guid}")
            return {"index": index, "success": False, "error": "Timed out"}
        except Exception as e:
            logger.error(f"[{index}] Set PIN error: {e}")
            return {"index": index, "success": False, "error": str(e)}

    async def _do_set_pin(self, page: Page, guid: str, pin: str, password: str, index: int) -> dict:
        try:
            logger.info(f"[{index}] Setting PIN for profile: {guid}")

            lock_url = f"https://www.netflix.com/settings/lock/{guid}"
            on_lock_page = False
            for nav_attempt in range(3):
                try:
                    await page.goto(lock_url, wait_until="domcontentloaded", timeout=20000)
                except Exception as nav_err:
                    if nav_attempt < 2:
                        await page.wait_for_timeout(1500)
                        continue
                    return {"index": index, "success": False, "error": f"Navigation failed: {short_error(nav_err)}"}

                if "login" in page.url.lower():
                    return {"index": index, "success": False, "error": "Session expired"}

                if "/browse" in page.url.lower() or "/profilesgate" in page.url.lower():
                    logger.warning(f"[{index}] PIN: Redirected to {page.url}, retrying...")
                    await page.wait_for_timeout(1500 * (nav_attempt + 1))
                    continue

                on_lock_page = True
                break

            if not on_lock_page:
                return {"index": index, "success": False, "error": "Could not reach lock page"}

            pin_btn_selectors = [
                "button:has-text('Edit PIN')",
                "button:has-text('Create a Profile Lock')",
                "button:has-text('Create Profile Lock')",
                "a:has-text('Edit PIN')",
                "a:has-text('Create a Profile Lock')",
            ]

            btn_clicked = False
            for retry in range(8):
                for selector in pin_btn_selectors:
                    el = page.locator(selector).first
                    if await el.count() > 0 and await el.is_visible():
                        await el.click()
                        btn_clicked = True
                        logger.info(f"[{index}] Clicked PIN button: {selector}")
                        break
                if btn_clicked:
                    break
                await page.wait_for_timeout(500)

            if not btn_clicked:
                return {"index": index, "success": False, "error": "No Edit PIN / Create Lock button found"}

            for wait in range(20):
                pin_input = page.locator("input[name='PIN']:visible").first
                if await pin_input.count() > 0:
                    logger.info(f"[{index}] PIN input visible (no MFA)")
                    break

                confirm = page.locator("button:has-text('Confirm password')").first
                if await confirm.count() > 0:
                    await confirm.click()
                    logger.info(f"[{index}] Clicked 'Confirm password'")

                    for t in range(15):
                        await page.wait_for_timeout(300)

                        pwd_input = page.locator("input[type='password']:visible").first
                        if await pwd_input.count() > 0:
                            await pwd_input.fill(password)
                            logger.info(f"[{index}] Entered password")

                            for s in ["button:has-text('Submit')", "button[type='submit']", "button:has-text('Continue')"]:
                                btn = page.locator(s).first
                                if await btn.count() > 0 and await btn.is_visible():
                                    await btn.click()
                                    break

                            for w in range(20):
                                await page.wait_for_timeout(250)
                                if "pinEntry" in page.url or "pinentry" in page.url.lower():
                                    break
                                wrong_pwd = await page.locator("text=Incorrect password").count() + \
                                            await page.locator("text=Wrong password").count()
                                if wrong_pwd > 0:
                                    return {"index": index, "success": False, "error": "Incorrect password"}
                                pin_c = page.locator("input[name='PIN']:visible").first
                                if await pin_c.count() > 0:
                                    break
                            break

                        pin_check = page.locator("input[name='PIN']:visible").first
                        if await pin_check.count() > 0:
                            break
                    break

                await page.wait_for_timeout(300)

            pin_filled = False
            for attempt in range(15):
                main_pin = page.locator("input[name='PIN']:visible").first
                if await main_pin.count() > 0:
                    await main_pin.click()
                    await main_pin.fill(pin)
                    logger.info(f"[{index}] Filled PIN: {pin}")
                    pin_filled = True
                    break

                numeric_pin = page.locator("input[inputmode='numeric']:visible").first
                if await numeric_pin.count() > 0:
                    await numeric_pin.click()
                    await numeric_pin.fill(pin)
                    pin_filled = True
                    break

                await page.wait_for_timeout(300)

            if not pin_filled:
                return {"index": index, "success": False, "error": "PIN input not found"}

            for sel in ["button:has-text('Save PIN')", "button:has-text('Save')"]:
                el = page.locator(sel).first
                if await el.count() > 0 and await el.is_visible():
                    await el.click()
                    logger.info(f"[{index}] Clicked {sel}")
                    break

            for w in range(20):
                await page.wait_for_timeout(250)
                if "profilePinUpdated=success" in page.url or "profilePinAdded=success" in page.url:
                    break

            success = "profilePinUpdated=success" in page.url or "profilePinAdded=success" in page.url
            logger.info(f"[{index}] PIN {'OK' if success else 'FAIL'}: {page.url}")
            return {"index": index, "success": success, "pin": pin}

        except Exception as e:
            logger.error(f"[{index}] Set PIN error: {e}")
            return {"index": index, "success": False, "error": str(e)}

    async def _set_pins_batch(self, batch: List[tuple], password: str) -> List[dict]:
        p = None
        browser = None
        try:
            p, browser, context = await self._launch_browser()
            page = await context.new_page()
            results = []
            for idx, guid, pin in batch:
                result = await self._set_pin_on_page(page, guid, pin, password, idx)
                results.append(result)
            await self._safe_close(p, browser)
            return results
        except Exception as e:
            logger.error(f"PIN batch error: {e}")
            await self._safe_close(p, browser)
            return [{"index": idx, "success": False, "error": str(e)} for idx, _, _ in batch]

    async def set_all_pins_parallel(self, profiles: List[dict], pins: List[str], password: str) -> List[dict]:
        items = []
        for i, (profile, pin) in enumerate(zip(profiles, pins)):
            guid = profile.get("guid", "")
            if guid:
                items.append((i, guid, pin))

        if not items:
            return [{"index": i, "success": False, "error": "No GUID"} for i in range(len(profiles))]

        n_workers = min(3, len(items))
        batches = [[] for _ in range(n_workers)]
        for j, item in enumerate(items):
            batches[j % n_workers].append(item)

        async def _staggered_batch(batch, delay):
            if delay > 0:
                await asyncio.sleep(delay)
            return await self._set_pins_batch(batch, password)

        logger.info(f"Setting PINs: {len(items)} profiles across {n_workers} parallel workers")
        batch_results = await asyncio.gather(
            *[_staggered_batch(batch, i * 1.0) for i, batch in enumerate(batches)],
            return_exceptions=True
        )

        results = [None] * len(profiles)
        for br in batch_results:
            if isinstance(br, Exception):
                continue
            for r in br:
                if isinstance(r, dict) and "index" in r:
                    results[r["index"]] = r

        for i in range(len(profiles)):
            if results[i] is None:
                results[i] = {"index": i, "success": False, "error": "Worker failed"}

        return results

    async def _delete_profile_lock(self, guid: str, password: str, index: int) -> dict:
        p = None
        browser = None
        try:
            p, browser, context = await self._launch_browser()
            page = await context.new_page()

            await page.goto(f"https://www.netflix.com/settings/lock/{guid}", wait_until="domcontentloaded")

            for _ in range(10):
                if "login" in page.url.lower():
                    await self._safe_close(p, browser)
                    return {"index": index, "success": False, "error": "Session expired"}
                delete_btn = page.locator("button:has-text('Delete Profile Lock'), button:has-text('Remove Lock')").first
                if await delete_btn.count() > 0:
                    break
                no_lock = page.locator("text=Profile Lock PIN, input[type='password']").first
                if await no_lock.count() == 0 and await page.locator("text=Create Lock").count() > 0:
                    await self._safe_close(p, browser)
                    return {"index": index, "success": True, "message": "No lock"}
                await page.wait_for_timeout(500)

            delete_btn = page.locator("button:has-text('Delete Profile Lock'), button:has-text('Remove Lock')").first
            if await delete_btn.count() == 0:
                await self._safe_close(p, browser)
                return {"index": index, "success": True, "message": "No lock to delete"}

            await delete_btn.click(force=True)

            for _ in range(20):
                pwd_input = page.locator("input[type='password']:visible").first
                if await pwd_input.count() > 0:
                    await pwd_input.fill(password)
                    await page.wait_for_timeout(200)
                    await page.keyboard.press("Enter")

                    for _ in range(20):
                        await page.wait_for_timeout(300)
                        if await page.locator("text=Incorrect password").count() > 0:
                            await self._safe_close(p, browser)
                            return {"index": index, "success": False, "error": "Incorrect password"}
                        if await page.locator("button:has-text('Delete Profile Lock'), button:has-text('Remove Lock')").count() == 0:
                            await self._safe_close(p, browser)
                            return {"index": index, "success": True, "message": "Lock deleted"}
                    break
                await page.wait_for_timeout(300)

            await self._safe_close(p, browser)
            return {"index": index, "success": True, "message": "Lock deleted"}

        except Exception as e:
            await self._safe_close(p, browser)
            return {"index": index, "success": False, "error": str(e)}

    async def delete_all_profile_locks(self, profiles: List[dict], password: str) -> List[dict]:
        processed = []
        for i, profile in enumerate(profiles):
            guid = profile.get("guid", "")
            if guid:
                try:
                    r = await self._delete_profile_lock(guid, password, i)
                    processed.append(r if isinstance(r, dict) else {"index": i, "success": False, "error": str(r)})
                except Exception as e:
                    processed.append({"index": i, "success": False, "error": str(e)})
        return processed

    async def _add_single_profile(self, name: str, index: int) -> dict:
        p = None
        browser = None
        try:
            p, browser, context = await self._launch_browser()
            page = await context.new_page()

            await page.goto("https://www.netflix.com/ManageProfiles", wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)

            if "login" in page.url.lower():
                await self._safe_close(p, browser)
                return {"index": index, "success": False, "error": "Session expired"}

            add_selectors = [
                "a:has-text('Add Profile')",
                "button:has-text('Add Profile')",
                "[data-uia='add-profile-button']",
                "text=Add Profile",
            ]

            add_clicked = False
            for selector in add_selectors:
                el = page.locator(selector).first
                if await el.count() > 0:
                    await el.click(force=True)
                    add_clicked = True
                    break

            if not add_clicked:
                await self._safe_close(p, browser)
                return {"index": index, "success": False, "error": "Add Profile button not found"}

            await page.wait_for_timeout(2000)

            name_selectors = [
                "input[data-uia='profile-name-entry']",
                "input[name='name']",
                "input[name='profileName']",
                "input[data-uia='profile-gate-add-profile-modal+name-input']",
                "input[type='text']:visible",
            ]

            name_input = None
            for selector in name_selectors:
                el = page.locator(selector).first
                if await el.count() > 0:
                    name_input = el
                    break

            if name_input is None or await name_input.count() == 0:
                all_inputs = await page.locator("input:visible").all()
                for inp in all_inputs:
                    inp_type = await inp.get_attribute("type") or "text"
                    if inp_type in ["text", ""]:
                        name_input = inp
                        break

            if name_input is None or await name_input.count() == 0:
                await self._safe_close(p, browser)
                return {"index": index, "success": False, "error": "Name input not found"}

            await name_input.fill(name)
            await page.wait_for_timeout(300)

            save_selectors = [
                "button:has-text('Save'):visible",
                "button:has-text('Continue'):visible",
                "button[data-uia='profile-save-button']",
                "button[type='submit']:visible",
            ]

            for selector in save_selectors:
                el = page.locator(selector).last
                if await el.count() > 0:
                    await el.click(force=True)
                    break

            await page.wait_for_timeout(2000)
            await self._safe_close(p, browser)
            return {"index": index, "success": True, "name": name}

        except Exception as e:
            logger.error(f"Add profile error: {e}")
            await self._safe_close(p, browser)
            return {"index": index, "success": False, "error": str(e)}

    async def add_profiles_parallel(self, names: List[str]) -> List[dict]:
        results = []
        for i, name in enumerate(names):
            result = await self._add_single_profile(name, i)
            results.append(result)
            await asyncio.sleep(0.5)
        return results

    async def take_profiles_screenshot(self) -> Optional[bytes]:
        p = None
        browser = None
        try:
            p, browser, context = await self._launch_browser()
            page = await context.new_page()
            await page.goto("https://www.netflix.com/ManageProfiles", wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
            screenshot = await page.screenshot(type='png')
            await self._safe_close(p, browser)
            return screenshot
        except Exception as e:
            logger.error(f"Screenshot error: {e}")
            await self._safe_close(p, browser)
            return None

    async def update_profile(self, guid: str, new_name: str, password: str = "") -> tuple:
        result = await self._update_single_profile(guid, new_name, password, 0)
        if result.get("success"):
            return True, f"Profile updated to '{new_name}'!"
        return False, result.get("error", "Unknown error")

    async def add_profile(self, name: str) -> tuple:
        result = await self._add_single_profile(name, 0)
        if result.get("success"):
            return True, f"Profile '{name}' created!"
        return False, result.get("error", "Failed")

    async def delete_profile(self, guid: str) -> tuple:
        p = None
        browser = None
        try:
            p, browser, context = await self._launch_browser()
            page = await context.new_page()

            await page.goto(f"https://www.netflix.com/settings/{guid}", wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)

            if "login" in page.url.lower():
                await self._safe_close(p, browser)
                return False, "Session expired"

            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1000)

            delete_btn = page.locator("button:has-text('Delete Profile')").first
            if await delete_btn.count() == 0:
                delete_btn = page.locator("a:has-text('Delete Profile')").first
            if await delete_btn.count() == 0:
                delete_btn = page.locator("text=Delete Profile").first

            if await delete_btn.count() > 0:
                await delete_btn.click(force=True)
                await page.wait_for_timeout(2000)

                confirm_selectors = [
                    "[data-uia='profile-settings-page+delete-profile+destructive-button']",
                    "button:has-text('Delete Profile')",
                    "button:has-text('Confirm')",
                    "button:has-text('Yes')",
                ]

                for selector in confirm_selectors:
                    el = page.locator(selector).last
                    if await el.count() > 0:
                        await el.click(force=True)
                        await page.wait_for_timeout(2000)
                        await self._safe_close(p, browser)
                        return True, "Profile deleted!"

                await self._safe_close(p, browser)
                return False, "Confirmation button not found"
            else:
                await self._safe_close(p, browser)
                return False, "Delete Profile button not found"

        except Exception as e:
            await self._safe_close(p, browser)
            return False, f"Error: {str(e)}"

    async def set_profile_pin(self, guid: str, pin: str, password: str = "") -> tuple:
        p = None
        browser = None
        try:
            p, browser, context = await self._launch_browser()
            page = await context.new_page()
            result = await self._set_pin_on_page(page, guid, pin, password, 0)
            await self._safe_close(p, browser)
            if result.get("success"):
                return True, "Profile PIN set!"
            return False, result.get("error", "Unknown error")
        except Exception as e:
            await self._safe_close(p, browser)
            return False, f"Error: {str(e)}"


async def is_authorized(user_id: int) -> bool:
    if user_id == HOST_USER_ID:
        return True
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM authorized_users WHERE user_id = %s", (user_id,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result is not None
    except:
        return False


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_authorized(user_id):
        await update.message.reply_text("You are not authorized.")
        return

    msg = (
        "*Netflix Profile Manager Bot*\n\n"
        "*Session Commands:*\n"
        "`/login <cookie>` - Login with Netflix cookie\n"
        "`/loginemail <email> <password>` - Login with email/password\n"
        "`/profiles` - List all profiles\n"
        "`/logout` - Clear session\n\n"
        "*Profile Management:*\n"
        "`/updateallprofiles <n1> <n2> ... <password>` - Update ALL names\n"
        "`/updateallpins <p1> <p2> ... <password>` - Set ALL PINs\n"
        "`/addprofile <name>` - Add new profile\n"
        "`/deleteprofile <guid>` - Delete profile\n"
        "`/updateprofile <guid> <name>` - Update single profile\n"
        "`/setpin <guid> <pin> <password>` - Set single PIN\n\n"
        "*Admin:*\n"
        "`/adduser <id>` | `/removeuser <id>` | `/listusers`\n\n"
        "Use `/help` for examples."
    )
    await update.message.reply_text(msg, parse_mode='Markdown')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_authorized(user_id):
        await update.message.reply_text("Not authorized.")
        return

    msg = (
        "*Help & Examples*\n\n"
        "*Bulk Update Examples:*\n"
        "`/updateallprofiles MOON SUN LIGHT DARK FUSION MyPassword`\n"
        "`/updateallpins 1111 2222 3333 4444 5555 MyPassword`\n\n"
        "Both commands run in PARALLEL (multiple browser tabs)!\n"
        "The LAST argument is always your Netflix account password.\n\n"
        "*Single Profile:*\n"
        "`/updateprofile <guid> NewName`\n"
        "`/setpin <guid> 1234 MyPassword`\n\n"
        "*Login:*\n"
        "Get cookie from browser DevTools > Application > Cookies\n"
        "Copy NetflixId and SecureNetflixId values\n\n"
        "*Note:* Profile updates use browser automation and may take 10-30 seconds."
    )
    await update.message.reply_text(msg, parse_mode='Markdown')


async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_authorized(user_id):
        await safe_reply(update.message, "Not authorized.")
        return

    if not context.args:
        await safe_reply(update.message, "Usage: `/login <cookie>`", parse_mode='Markdown')
        return

    cookie = ' '.join(context.args)
    msg = await update.message.reply_text("Validating session...")

    try:
        netflix = NetflixBrowser(cookie)
        valid, result = await netflix.validate_session()

        if valid:
            netflix_sessions[user_id] = {"browser": netflix, "cookie": cookie}
            await safe_edit(msg, "Login Successful!\nUse /profiles to see profiles.")
        else:
            await safe_edit(msg, f"Failed: {result}")
    except Exception as e:
        logger.error(f"Login error: {e}")
        await safe_edit(msg, f"Error: {short_error(e)}")


async def loginemail_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_authorized(user_id):
        await safe_reply(update.message, "Not authorized.")
        return

    if len(context.args) < 2:
        await safe_reply(update.message, "Usage: /loginemail <email> <password>")
        return

    email = context.args[0]
    password = ' '.join(context.args[1:])

    msg = await update.message.reply_text("Logging in with email/password...\nThis may take a moment...")

    try:
        success, result, cookie = await NetflixBrowser.login_with_credentials(email, password)

        if success and cookie:
            netflix = NetflixBrowser(cookie)
            netflix_sessions[user_id] = {"browser": netflix, "cookie": cookie}
            await safe_edit(msg, 
                "Login Successful!\n"
                f"Email: {email}\n\n"
                "Use /profiles to see profiles."
            )
        else:
            await safe_edit(msg, f"Failed: {result}")
    except Exception as e:
        logger.error(f"Login email error: {e}")
        await safe_edit(msg, f"Error: {short_error(e)}")


async def logout_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in netflix_sessions:
        netflix_sessions.pop(user_id)
        await safe_reply(update.message, "Logged out!")
    else:
        await safe_reply(update.message, "Not logged in.")


async def profiles_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_authorized(user_id):
        await safe_reply(update.message, "Not authorized.")
        return

    if user_id not in netflix_sessions:
        await safe_reply(update.message, "Login first: /login <cookie>")
        return

    msg = await update.message.reply_text("Fetching profiles...")

    try:
        netflix = netflix_sessions[user_id]["browser"]
        success, data = await netflix.get_profiles()

        if success:
            profiles = data.get("profiles", [])
            if profiles:
                text = "Netflix Profiles:\n\n"
                for i, p in enumerate(profiles, 1):
                    kids_tag = " [Kids]" if p.get("isKids", False) else ""
                    text += f"{i}. {p['profileName']}{kids_tag}\n   GUID: {p['guid']}\n\n"
                text += f"Total: {len(profiles)} profiles"
                await safe_edit(msg, text)
            else:
                await safe_edit(msg, "No profiles found.")
        else:
            await safe_edit(msg, f"Failed: {data}")
    except Exception as e:
        logger.error(f"Profiles error: {e}")
        await safe_edit(msg, f"Error: {short_error(e)}")


async def updateallprofiles_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_authorized(user_id):
        await safe_reply(update.message, "Not authorized.")
        return

    if user_id not in netflix_sessions:
        await safe_reply(update.message, "Login first.")
        return

    if not context.args or len(context.args) < 2:
        await safe_reply(update.message, 
            "Usage: /updateallprofiles name1 name2 ... password\n"
            "(Last argument is your Netflix account password)"
        )
        return

    args = list(context.args)
    password = args.pop()
    new_names = args

    if not new_names:
        await safe_reply(update.message, "Please provide profile names.")
        return

    msg = await update.message.reply_text("Fetching profiles...")

    try:
        netflix = netflix_sessions[user_id]["browser"]
        success, data = await netflix.get_profiles()

        if not success:
            await safe_edit(msg, f"Failed to fetch profiles: {data}")
            return

        profiles = data.get("profiles", [])
        existing_count = len(profiles)
        names_count = len(new_names)

        kids_profiles = [p for p in profiles if p.get("isKids", False)]
        regular_profiles = [p for p in profiles if not p.get("isKids", False)]
        kids_count = len(kids_profiles)

        missing_count = max(0, names_count - existing_count)

        info_text = f"Found {existing_count} profiles"
        if kids_count > 0:
            info_text += f" ({kids_count} Kids)"
        info_text += f"\nNames to set: {names_count}"
        if missing_count > 0:
            info_text += f"\nWill add {missing_count} missing profile(s)"
        await safe_edit(msg, info_text)
        await asyncio.sleep(1)

        results = []
        name_idx = 0

        regular_to_update = min(len(regular_profiles), names_count)
        if regular_to_update > 0:
            await safe_edit(msg, f"Updating {regular_to_update} profiles (MFA-blocked ones will be recreated)...")

            update_profiles = regular_profiles[:regular_to_update]
            update_names = new_names[:regular_to_update]
            update_results = await netflix.update_all_profiles_parallel(update_profiles, update_names, password)

            for i, (profile, result) in enumerate(zip(update_profiles, update_results)):
                old_name = profile.get("profileName", "Unknown")
                new_name = update_names[i]
                if isinstance(result, dict) and result.get("success"):
                    results.append(f"OK {i+1}. {old_name} -> {new_name}")
                else:
                    error = result.get("error", "Failed") if isinstance(result, dict) else str(result)
                    results.append(f"FAIL {i+1}. {old_name} -> {new_name} ({error})")

            name_idx = regular_to_update

        if kids_count > 0 and name_idx < names_count:
            await safe_edit(msg, f"Removing {kids_count} Kids profiles and creating new ones...")

            deleted_count = 0
            for kids_profile in kids_profiles:
                guid = kids_profile.get("guid")
                profile_name = kids_profile.get("profileName", "Kids")
                if guid:
                    success_del, delete_msg = await netflix.delete_profile(guid)
                    if success_del:
                        deleted_count += 1
                        logger.info(f"Deleted Kids profile: {profile_name}")
                    else:
                        logger.error(f"Failed to delete Kids profile {profile_name}: {delete_msg}")
                    await asyncio.sleep(1)

            logger.info(f"Deleted {deleted_count}/{kids_count} Kids profiles")

            remaining_names = new_names[name_idx:name_idx + kids_count]
            if remaining_names:
                add_results = await netflix.add_profiles_parallel(remaining_names)
                for i, (name, result) in enumerate(zip(remaining_names, add_results)):
                    idx = name_idx + i + 1
                    if isinstance(result, dict) and result.get("success"):
                        results.append(f"OK {idx}. Kids->NEW: {name}")
                    else:
                        error = result.get("error", "Failed") if isinstance(result, dict) else str(result)
                        results.append(f"FAIL {idx}. Kids->NEW: {name} ({error})")
                name_idx += len(remaining_names)

        profiles_to_add = names_count - name_idx
        if profiles_to_add > 0:
            await safe_edit(msg, f"Adding {profiles_to_add} new profiles...")
            add_names = new_names[name_idx:]
            add_results = await netflix.add_profiles_parallel(add_names)
            for i, (name, result) in enumerate(zip(add_names, add_results)):
                idx = name_idx + i + 1
                if isinstance(result, dict) and result.get("success"):
                    results.append(f"OK {idx}. NEW: {name}")
                else:
                    error = result.get("error", "Failed") if isinstance(result, dict) else str(result)
                    results.append(f"FAIL {idx}. NEW: {name} ({error})")

        success_count = sum(1 for r in results if r.startswith("OK"))

        text = "Profile Update Results:\n\n"
        text += "\n".join(results)
        text += f"\n\n{success_count}/{names_count} completed!"

        await safe_edit(msg, text)

        try:
            screenshot = await netflix.take_profiles_screenshot()
            if screenshot:
                await update.message.reply_photo(
                    photo=InputFile(io.BytesIO(screenshot), filename="profiles.png"),
                    caption="Updated profiles"
                )
        except Exception as ss_err:
            logger.error(f"Screenshot error: {ss_err}")

    except Exception as e:
        logger.error(f"Update all profiles error: {e}")
        try:
            await safe_edit(msg, f"Error: {short_error(e)}")
        except:
            pass


async def updateallpins_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_authorized(user_id):
        await safe_reply(update.message, "Not authorized.")
        return

    if user_id not in netflix_sessions:
        await safe_reply(update.message, "Login first.")
        return

    if len(context.args) < 2:
        await safe_reply(update.message, 
            "Usage: /updateallpins pin1 pin2 ... password\n"
            "Example: /updateallpins 1111 2222 3333 4444 5555 MyPass"
        )
        return

    password = context.args[-1]
    pins = list(context.args[:-1])

    for i, pin in enumerate(pins):
        if len(pin) != 4 or not pin.isdigit():
            await safe_reply(update.message, f"PIN #{i+1} '{pin}' invalid. Must be 4 digits.")
            return

    msg = await update.message.reply_text("Fetching profiles...")

    try:
        netflix = netflix_sessions[user_id]["browser"]
        success, data = await netflix.get_profiles()

        if not success:
            await safe_edit(msg, f"Failed: {data}")
            return

        all_profiles = data.get("profiles", [])
        regular_profiles = [p for p in all_profiles if not p.get("isKids", False)]
        kids_profiles = [p for p in all_profiles if p.get("isKids", False)]

        if kids_profiles:
            await safe_edit(msg, 
                f"Found {len(all_profiles)} profiles ({len(kids_profiles)} Kids - skipped)\n"
                f"Setting PINs for {len(regular_profiles)} regular profiles"
            )

        if len(pins) != len(regular_profiles):
            await safe_edit(msg, 
                f"Got {len(pins)} PINs but {len(regular_profiles)} regular profiles!\n"
                f"(Kids profiles: {len(kids_profiles)} - skipped)"
            )
            return

        await safe_edit(msg, f"Setting {len(regular_profiles)} PINs in PARALLEL...")

        results = await netflix.set_all_pins_parallel(regular_profiles, pins, password)

        lines = []
        for i, (profile, result) in enumerate(zip(regular_profiles, results)):
            name = profile.get("profileName", "Unknown")
            pin = pins[i]
            if isinstance(result, dict) and result.get("success"):
                lines.append(f"OK {i+1}. {name} -> PIN: {pin}")
            else:
                error = result.get("error", "Failed") if isinstance(result, dict) else str(result)
                lines.append(f"FAIL {i+1}. {name} ({error})")

        for kids_profile in kids_profiles:
            lines.append(f"SKIP {kids_profile.get('profileName', 'Kids')} (Kids profile)")

        success_count = sum(1 for r in results if isinstance(r, dict) and r.get("success"))

        text = "PIN Update Results:\n\n"
        text += "\n".join(lines)
        text += f"\n\n{success_count}/{len(regular_profiles)} PINs set!"

        await safe_edit(msg, text)

        try:
            screenshot = await netflix.take_profiles_screenshot()
            if screenshot:
                await update.message.reply_photo(
                    photo=InputFile(io.BytesIO(screenshot), filename="pins.png"),
                    caption="PINs updated"
                )
        except Exception as ss_err:
            logger.error(f"Screenshot error: {ss_err}")

    except Exception as e:
        logger.error(f"Update all pins error: {e}")
        try:
            await safe_edit(msg, f"Error: {short_error(e)}")
        except:
            pass


async def addprofile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_authorized(user_id):
        await safe_reply(update.message, "Not authorized.")
        return

    if user_id not in netflix_sessions:
        await safe_reply(update.message, "Login first: /login <cookie>")
        return

    if not context.args:
        await safe_reply(update.message, "Usage: /addprofile <name>")
        return

    name = ' '.join(context.args)
    msg = await update.message.reply_text(f"Creating profile '{name}'...")

    netflix = netflix_sessions[user_id]["browser"]
    success, result = await netflix.add_profile(name)
    await safe_edit(msg, f"{'OK' if success else 'FAIL'}: {result}")


async def updateprofile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_authorized(user_id):
        await safe_reply(update.message, "Not authorized.")
        return

    if user_id not in netflix_sessions:
        await safe_reply(update.message, "Login first: /login <cookie>")
        return

    if len(context.args) < 2:
        await safe_reply(update.message, "Usage: /updateprofile <guid> <name>")
        return

    guid = context.args[0]
    name = ' '.join(context.args[1:])
    msg = await update.message.reply_text(f"Updating profile to '{name}'...")

    netflix = netflix_sessions[user_id]["browser"]
    success, result = await netflix.update_profile(guid, name)
    await safe_edit(msg, f"{'OK' if success else 'FAIL'}: {result}")


async def deleteprofile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_authorized(user_id):
        await safe_reply(update.message, "Not authorized.")
        return

    if user_id not in netflix_sessions:
        await safe_reply(update.message, "Login first: /login <cookie>")
        return

    if not context.args:
        await safe_reply(update.message, "Usage: /deleteprofile <guid>")
        return

    guid = context.args[0]
    msg = await update.message.reply_text("Deleting profile...")

    netflix = netflix_sessions[user_id]["browser"]
    success, result = await netflix.delete_profile(guid)
    await safe_edit(msg, f"{'OK' if success else 'FAIL'}: {result}")


async def setpin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_authorized(user_id):
        await safe_reply(update.message, "Not authorized.")
        return

    if user_id not in netflix_sessions:
        await safe_reply(update.message, "Login first: /login <cookie>")
        return

    if len(context.args) < 3:
        await safe_reply(update.message, "Usage: /setpin <guid> <pin> <password>")
        return

    guid, pin, password = context.args[0], context.args[1], context.args[2]

    if len(pin) != 4 or not pin.isdigit():
        await safe_reply(update.message, "PIN must be exactly 4 digits.")
        return

    msg = await update.message.reply_text("Setting PIN...")

    netflix = netflix_sessions[user_id]["browser"]
    success, result = await netflix.set_profile_pin(guid, pin, password)
    await safe_edit(msg, f"{'OK' if success else 'FAIL'}: {result}")


async def adduser_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != HOST_USER_ID:
        await safe_reply(update.message, "Admin only.")
        return

    if not context.args:
        await safe_reply(update.message, "Usage: /adduser <telegram_id>")
        return

    try:
        new_id = int(context.args[0])
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM authorized_users WHERE user_id = %s", (new_id,))
        if cur.fetchone():
            await safe_reply(update.message, f"User {new_id} already authorized.")
            cur.close()
            conn.close()
            return

        cur.execute("INSERT INTO authorized_users (user_id, added_by) VALUES (%s, %s)", (new_id, user_id))
        conn.commit()
        cur.close()
        conn.close()
        await safe_reply(update.message, f"User {new_id} authorized!")
    except ValueError:
        await safe_reply(update.message, "Invalid ID. Must be a number.")
    except Exception as e:
        logger.error(f"Add user error: {e}")
        await safe_reply(update.message, f"Error: {short_error(e)}")


async def removeuser_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != HOST_USER_ID:
        await safe_reply(update.message, "Admin only.")
        return

    if not context.args:
        await safe_reply(update.message, "Usage: /removeuser <telegram_id>")
        return

    try:
        remove_id = int(context.args[0])
        if remove_id == HOST_USER_ID:
            await safe_reply(update.message, "Can't remove the host user.")
            return

        conn = get_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM authorized_users WHERE user_id = %s", (remove_id,))
        deleted = cur.rowcount
        conn.commit()
        cur.close()
        conn.close()

        if deleted > 0:
            netflix_sessions.pop(remove_id, None)
            await safe_reply(update.message, f"User {remove_id} removed.")
        else:
            await safe_reply(update.message, f"User {remove_id} not found.")
    except ValueError:
        await safe_reply(update.message, "Invalid ID. Must be a number.")
    except Exception as e:
        logger.error(f"Remove user error: {e}")
        await safe_reply(update.message, f"Error: {short_error(e)}")


async def listusers_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != HOST_USER_ID:
        await safe_reply(update.message, "Admin only.")
        return

    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT user_id FROM authorized_users")
        users = cur.fetchall()
        cur.close()
        conn.close()

        msg = f"*Host:* `{HOST_USER_ID}`\n\n"
        if users:
            msg += "*Authorized Users:*\n" + "\n".join([f"- `{u['user_id']}`" for u in users])
        else:
            msg += "No other authorized users."
        await safe_reply(update.message, msg, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"List users error: {e}")
        await safe_reply(update.message, f"Error: {short_error(e)}")


async def main():
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        return

    if HOST_USER_ID == 0:
        logger.warning("HOST_USER_ID not set! Only users added to DB will have access.")

    init_db()

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("login", login_command))
    app.add_handler(CommandHandler("loginemail", loginemail_command))
    app.add_handler(CommandHandler("logout", logout_command))
    app.add_handler(CommandHandler("profiles", profiles_command))
    app.add_handler(CommandHandler("addprofile", addprofile_command))
    app.add_handler(CommandHandler("updateprofile", updateprofile_command))
    app.add_handler(CommandHandler("updateallprofiles", updateallprofiles_command))
    app.add_handler(CommandHandler("deleteprofile", deleteprofile_command))
    app.add_handler(CommandHandler("setpin", setpin_command))
    app.add_handler(CommandHandler("updateallpins", updateallpins_command))
    app.add_handler(CommandHandler("adduser", adduser_command))
    app.add_handler(CommandHandler("removeuser", removeuser_command))
    app.add_handler(CommandHandler("listusers", listusers_command))

    logger.info(f"Bot starting... Host user: {HOST_USER_ID}")

    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    logger.info("Telegram bot is running!")

    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down...")
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
