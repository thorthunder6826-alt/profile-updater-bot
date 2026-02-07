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
            viewport={"width": 1280, "height": 900},
            locale="en-US"
        )
        await context.add_cookies(self.cookies)
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

    async def _update_profile_on_page(self, page: Page, guid: str, new_name: str, index: int) -> dict:
        try:
            return await asyncio.wait_for(
                self._do_update_profile(page, guid, new_name, index),
                timeout=45.0
            )
        except asyncio.TimeoutError:
            logger.error(f"[{index}] Profile update timed out for {guid}")
            return {"index": index, "success": False, "error": "Timed out after 45s"}
        except Exception as e:
            logger.error(f"[{index}] Update profile error: {e}")
            return {"index": index, "success": False, "error": str(e)}

    async def _do_update_profile(self, page: Page, guid: str, new_name: str, index: int) -> dict:
        logger.info(f"[{index}] Updating profile: {guid} -> {new_name}")

        try:
            await page.goto(
                f"https://www.netflix.com/settings/manage/profile/{guid}",
                wait_until="domcontentloaded",
                timeout=15000
            )
        except Exception:
            logger.info(f"[{index}] /settings/manage/profile/ failed, trying /settings/")
            try:
                await page.goto(
                    f"https://www.netflix.com/settings/{guid}",
                    wait_until="domcontentloaded",
                    timeout=15000
                )
            except Exception as nav_err:
                return {"index": index, "success": False, "error": f"Navigation failed: {nav_err}"}

        await page.wait_for_timeout(2000)

        if "login" in page.url.lower():
            return {"index": index, "success": False, "error": "Session expired"}

        all_inputs = await page.locator("input:visible").all()
        logger.info(f"[{index}] Page URL: {page.url}, visible inputs: {len(all_inputs)}")

        name_selectors = [
            "input[data-uia='profile-name-entry']",
            "input#profile-name-entry",
            "input[name='profileName']",
            "input[name='profile-name']",
            "input[id*='profile-name']",
            "input[class*='profile-name']",
            "input[placeholder*='Name']",
        ]

        name_input = None
        for selector in name_selectors:
            el = page.locator(selector).first
            if await el.count() > 0:
                name_input = el
                logger.info(f"[{index}] Found name input: {selector}")
                break

        if name_input is None:
            edit_btn_selectors = [
                "button:has-text('Edit')",
                "a:has-text('Edit')",
                "[data-uia*='edit']",
            ]
            for selector in edit_btn_selectors:
                el = page.locator(selector).first
                if await el.count() > 0:
                    await el.click(force=True)
                    logger.info(f"[{index}] Clicked edit button: {selector}")
                    await page.wait_for_timeout(1500)
                    break

            for selector in name_selectors:
                el = page.locator(selector).first
                if await el.count() > 0:
                    name_input = el
                    logger.info(f"[{index}] Found name input after edit click: {selector}")
                    break

        if name_input is None:
            for inp in all_inputs:
                inp_type = await inp.get_attribute("type") or "text"
                inp_name = await inp.get_attribute("name") or ""
                inp_id = await inp.get_attribute("id") or ""
                if inp_type in ["text", ""] and "search" not in inp_name.lower():
                    name_input = inp
                    logger.info(f"[{index}] Fallback: using text input name={inp_name} id={inp_id}")
                    break

        if name_input is None:
            logger.error(f"[{index}] Name input not found. URL: {page.url}")
            return {"index": index, "success": False, "error": f"Name input not found on {page.url}"}

        await name_input.click()
        await name_input.press("Control+a")
        await name_input.fill("")
        await page.wait_for_timeout(100)
        await name_input.type(new_name, delay=20)
        await page.wait_for_timeout(300)

        save_selectors = [
            "button[data-uia='profile-save-button']",
            "button:has-text('Save')",
            "button:has-text('Done')",
            "button[type='submit']",
        ]

        save_clicked = False
        for selector in save_selectors:
            el = page.locator(selector).first
            if await el.count() > 0:
                await el.click(force=True)
                save_clicked = True
                logger.info(f"[{index}] Clicked save: {selector}")
                break

        if not save_clicked:
            await page.keyboard.press("Enter")
            logger.info(f"[{index}] Pressed Enter to save")

        await page.wait_for_timeout(2000)
        logger.info(f"[{index}] Profile update completed: {new_name}")
        return {"index": index, "success": True, "new_name": new_name}

    async def _update_single_profile(self, guid: str, new_name: str, index: int) -> dict:
        p = None
        browser = None
        try:
            p, browser, context = await self._launch_browser()
            page = await context.new_page()
            result = await self._update_profile_on_page(page, guid, new_name, index)
            await self._safe_close(p, browser)
            return result
        except Exception as e:
            await self._safe_close(p, browser)
            return {"index": index, "success": False, "error": str(e)}

    async def update_all_profiles_parallel(self, profiles: List[dict], new_names: List[str]) -> List[dict]:
        p = None
        browser = None
        try:
            p, browser, context = await self._launch_browser()

            pages = []
            for _ in profiles:
                pages.append(await context.new_page())

            tasks = []
            for i, (profile, new_name, page) in enumerate(zip(profiles, new_names, pages)):
                guid = profile.get("guid", "")
                if guid:
                    tasks.append(self._update_profile_on_page(page, guid, new_name, i))

            if not tasks:
                await self._safe_close(p, browser)
                return []

            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=120.0
                )
            except asyncio.TimeoutError:
                logger.error("Overall parallel update timed out after 120s")
                await self._safe_close(p, browser)
                return [{"index": i, "success": False, "error": "Overall timeout"} for i in range(len(profiles))]

            processed = []
            for i, r in enumerate(results):
                if isinstance(r, Exception):
                    processed.append({"index": i, "success": False, "error": str(r)})
                elif isinstance(r, dict):
                    processed.append(r)
                else:
                    processed.append({"index": i, "success": False, "error": f"Unexpected result: {r}"})

            await self._safe_close(p, browser)
            return processed

        except Exception as e:
            logger.error(f"Parallel update error: {e}")
            await self._safe_close(p, browser)
            return [{"index": i, "success": False, "error": str(e)} for i in range(len(profiles))]

    async def _set_pin_on_page(self, page: Page, guid: str, pin: str, password: str, index: int) -> dict:
        try:
            return await asyncio.wait_for(
                self._do_set_pin(page, guid, pin, password, index),
                timeout=45.0
            )
        except asyncio.TimeoutError:
            logger.error(f"[{index}] PIN set timed out for {guid}")
            return {"index": index, "success": False, "error": "Timed out after 45s"}
        except Exception as e:
            logger.error(f"[{index}] Set PIN error: {e}")
            return {"index": index, "success": False, "error": str(e)}

    async def _do_set_pin(self, page: Page, guid: str, pin: str, password: str, index: int) -> dict:
        try:
            logger.info(f"[{index}] Setting PIN for profile: {guid}")

            await page.goto(f"https://www.netflix.com/settings/lock/{guid}", wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(2000)

            if "login" in page.url.lower():
                return {"index": index, "success": False, "error": "Session expired"}

            pin_btn_selectors = [
                "button:has-text('Edit PIN')",
                "button:has-text('Create a Profile Lock')",
                "button:has-text('Create Profile Lock')",
                "button:has-text('Change')",
                "a:has-text('Edit PIN')",
                "a:has-text('Create a Profile Lock')",
            ]

            btn_clicked = False
            for selector in pin_btn_selectors:
                el = page.locator(selector).first
                if await el.count() > 0:
                    await el.click(force=True)
                    btn_clicked = True
                    logger.info(f"[{index}] Clicked PIN button: {selector}")
                    break

            if not btn_clicked:
                logger.warning(f"[{index}] No PIN button found, trying direct PIN input")

            await page.wait_for_timeout(1500)

            pwd_selectors = [
                "input[type='password']:visible",
                "input[data-uia='field-password']:visible",
                "input[name='password']:visible",
            ]

            for selector in pwd_selectors:
                pwd_input = page.locator(selector).first
                if await pwd_input.count() > 0:
                    await pwd_input.fill(password)
                    await page.wait_for_timeout(300)

                    submit_selectors = [
                        "button:has-text('Continue')",
                        "button:has-text('Submit')",
                        "button:has-text('Confirm')",
                        "button[type='submit']",
                    ]
                    submitted = False
                    for sub_sel in submit_selectors:
                        sub_btn = page.locator(sub_sel).first
                        if await sub_btn.count() > 0:
                            await sub_btn.click(force=True)
                            submitted = True
                            break
                    if not submitted:
                        await page.keyboard.press("Enter")

                    await page.wait_for_timeout(2000)

                    if await page.locator("text=Incorrect password").count() > 0 or \
                       await page.locator("text=Wrong password").count() > 0:
                        return {"index": index, "success": False, "error": "Incorrect password"}
                    break

            pin_selectors = [
                "input[inputmode='numeric']:visible",
                "input[maxlength='4']:visible",
                "input[data-uia*='pin']:visible",
                "input[name*='pin']:visible",
                "input[type='tel']:visible",
            ]

            pin_input = None
            for _ in range(5):
                for selector in pin_selectors:
                    el = page.locator(selector).first
                    if await el.count() > 0:
                        pin_input = el
                        logger.info(f"[{index}] Found PIN input: {selector}")
                        break
                if pin_input:
                    break
                await page.wait_for_timeout(500)

            if pin_input and await pin_input.count() > 0:
                await pin_input.click()
                await pin_input.fill(pin)
                await page.wait_for_timeout(300)

                save_selectors = [
                    "button:has-text('Save'):visible",
                    "button:has-text('Done'):visible",
                    "button[type='submit']:visible",
                ]
                for selector in save_selectors:
                    el = page.locator(selector).last
                    if await el.count() > 0:
                        await el.click(force=True)
                        logger.info(f"[{index}] Clicked save: {selector}")
                        break

                await page.wait_for_timeout(1500)
                logger.info(f"[{index}] PIN set successfully: {pin}")
                return {"index": index, "success": True, "pin": pin}
            else:
                return {"index": index, "success": False, "error": "PIN input not found"}

        except Exception as e:
            logger.error(f"[{index}] Set PIN error: {e}")
            return {"index": index, "success": False, "error": str(e)}

    async def set_all_pins_parallel(self, profiles: List[dict], pins: List[str], password: str) -> List[dict]:
        p = None
        browser = None
        try:
            p, browser, context = await self._launch_browser()

            pages = []
            for _ in profiles:
                pages.append(await context.new_page())

            tasks = []
            for i, (profile, pin, page) in enumerate(zip(profiles, pins, pages)):
                guid = profile.get("guid", "")
                if guid:
                    tasks.append(self._set_pin_on_page(page, guid, pin, password, i))

            if not tasks:
                await self._safe_close(p, browser)
                return []

            results = await asyncio.gather(*tasks, return_exceptions=True)

            processed = []
            for i, r in enumerate(results):
                if isinstance(r, Exception):
                    processed.append({"index": i, "success": False, "error": str(r)})
                elif isinstance(r, dict):
                    processed.append(r)
                else:
                    processed.append({"index": i, "success": False, "error": f"Unexpected result: {r}"})

            await self._safe_close(p, browser)
            return processed

        except Exception as e:
            logger.error(f"Parallel PIN error: {e}")
            await self._safe_close(p, browser)
            return [{"index": i, "success": False, "error": str(e)} for i in range(len(profiles))]

    async def _delete_profile_lock(self, guid: str, password: str, index: int) -> dict:
        p = None
        browser = None
        try:
            p, browser, context = await self._launch_browser()
            page = await context.new_page()

            await page.goto(f"https://www.netflix.com/settings/lock/{guid}", wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)

            if "login" in page.url.lower():
                await self._safe_close(p, browser)
                return {"index": index, "success": False, "error": "Session expired"}

            delete_btn = page.locator("button:has-text('Delete Profile Lock')").first
            if await delete_btn.count() == 0:
                delete_btn = page.locator("button:has-text('Remove Lock')").first
            if await delete_btn.count() == 0:
                await self._safe_close(p, browser)
                return {"index": index, "success": True, "message": "No lock to delete"}

            await delete_btn.click(force=True)
            await page.wait_for_timeout(2000)

            pwd_input = page.locator("input[type='password']:visible").first
            if await pwd_input.count() > 0:
                await pwd_input.fill(password)
                await page.wait_for_timeout(300)
                await page.keyboard.press("Enter")
                await page.wait_for_timeout(2500)

                if await page.locator("text=Incorrect password").count() > 0:
                    await self._safe_close(p, browser)
                    return {"index": index, "success": False, "error": "Incorrect password"}

            await self._safe_close(p, browser)
            return {"index": index, "success": True, "message": "Lock deleted"}

        except Exception as e:
            await self._safe_close(p, browser)
            return {"index": index, "success": False, "error": str(e)}

    async def delete_all_profile_locks(self, profiles: List[dict], password: str) -> List[dict]:
        tasks = []
        for i, profile in enumerate(profiles):
            guid = profile.get("guid", "")
            if guid:
                tasks.append(self._delete_profile_lock(guid, password, i))
        if not tasks:
            return []
        results = await asyncio.gather(*tasks, return_exceptions=True)
        processed = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                processed.append({"index": i, "success": False, "error": str(r)})
            elif isinstance(r, dict):
                processed.append(r)
            else:
                processed.append({"index": i, "success": False, "error": str(r)})
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

    async def update_profile(self, guid: str, new_name: str) -> tuple:
        result = await self._update_single_profile(guid, new_name, 0)
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
        await update.message.reply_text("Not authorized.")
        return

    if not context.args:
        await update.message.reply_text("Usage: `/login <cookie>`", parse_mode='Markdown')
        return

    cookie = ' '.join(context.args)
    msg = await update.message.reply_text("Validating session...")

    try:
        netflix = NetflixBrowser(cookie)
        valid, result = await netflix.validate_session()

        if valid:
            netflix_sessions[user_id] = {"browser": netflix, "cookie": cookie}
            await msg.edit_text("Login Successful!\nUse /profiles to see profiles.")
        else:
            await msg.edit_text(f"Failed: {result}")
    except Exception as e:
        logger.error(f"Login error: {e}")
        await msg.edit_text(f"Error: {str(e)}")


async def loginemail_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_authorized(user_id):
        await update.message.reply_text("Not authorized.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Usage: /loginemail <email> <password>")
        return

    email = context.args[0]
    password = ' '.join(context.args[1:])

    msg = await update.message.reply_text("Logging in with email/password...\nThis may take a moment...")

    try:
        success, result, cookie = await NetflixBrowser.login_with_credentials(email, password)

        if success and cookie:
            netflix = NetflixBrowser(cookie)
            netflix_sessions[user_id] = {"browser": netflix, "cookie": cookie}
            await msg.edit_text(
                "Login Successful!\n"
                f"Email: {email}\n\n"
                "Use /profiles to see profiles."
            )
        else:
            await msg.edit_text(f"Failed: {result}")
    except Exception as e:
        logger.error(f"Login email error: {e}")
        await msg.edit_text(f"Error: {str(e)}")


async def logout_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in netflix_sessions:
        netflix_sessions.pop(user_id)
        await update.message.reply_text("Logged out!")
    else:
        await update.message.reply_text("Not logged in.")


async def profiles_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_authorized(user_id):
        await update.message.reply_text("Not authorized.")
        return

    if user_id not in netflix_sessions:
        await update.message.reply_text("Login first: /login <cookie>")
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
                await msg.edit_text(text)
            else:
                await msg.edit_text("No profiles found.")
        else:
            await msg.edit_text(f"Failed: {data}")
    except Exception as e:
        logger.error(f"Profiles error: {e}")
        await msg.edit_text(f"Error: {str(e)}")


async def updateallprofiles_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_authorized(user_id):
        await update.message.reply_text("Not authorized.")
        return

    if user_id not in netflix_sessions:
        await update.message.reply_text("Login first.")
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /updateallprofiles name1 name2 ... password\n"
            "(Last argument is your Netflix account password)"
        )
        return

    args = list(context.args)
    password = args.pop()
    new_names = args

    if not new_names:
        await update.message.reply_text("Please provide profile names.")
        return

    msg = await update.message.reply_text("Fetching profiles...")

    try:
        netflix = netflix_sessions[user_id]["browser"]
        success, data = await netflix.get_profiles()

        if not success:
            await msg.edit_text(f"Failed to fetch profiles: {data}")
            return

        profiles = data.get("profiles", [])
        existing_count = len(profiles)
        names_count = len(new_names)

        kids_profiles = [p for p in profiles if p.get("isKids", False)]
        regular_profiles = [p for p in profiles if not p.get("isKids", False)]
        kids_count = len(kids_profiles)

        need_to_add = names_count > existing_count

        if need_to_add and profiles:
            await msg.edit_text("Removing profile locks first...")
            lock_results = await netflix.delete_all_profile_locks(profiles, password)
            deleted_locks = sum(1 for r in lock_results if isinstance(r, dict) and r.get("success"))
            logger.info(f"Deleted {deleted_locks}/{len(profiles)} profile locks")

        info_text = f"Found {existing_count} profiles"
        if kids_count > 0:
            info_text += f" ({kids_count} Kids)"
        info_text += f"\nNames to set: {names_count}"
        await msg.edit_text(info_text)
        await asyncio.sleep(1)

        results = []
        name_idx = 0

        regular_to_update = min(len(regular_profiles), names_count)
        if regular_to_update > 0:
            await msg.edit_text(f"Updating {regular_to_update} regular profiles in parallel...")

            update_profiles = regular_profiles[:regular_to_update]
            update_names = new_names[:regular_to_update]
            update_results = await netflix.update_all_profiles_parallel(update_profiles, update_names)

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
            await msg.edit_text(f"Removing {kids_count} Kids profiles and creating new ones...")

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
            await msg.edit_text(f"Adding {profiles_to_add} new profiles...")
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

        await msg.edit_text(text)

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
            await msg.edit_text(f"Error: {str(e)}")
        except:
            pass


async def updateallpins_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_authorized(user_id):
        await update.message.reply_text("Not authorized.")
        return

    if user_id not in netflix_sessions:
        await update.message.reply_text("Login first.")
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /updateallpins pin1 pin2 ... password\n"
            "Example: /updateallpins 1111 2222 3333 4444 5555 MyPass"
        )
        return

    password = context.args[-1]
    pins = list(context.args[:-1])

    for i, pin in enumerate(pins):
        if len(pin) != 4 or not pin.isdigit():
            await update.message.reply_text(f"PIN #{i+1} '{pin}' invalid. Must be 4 digits.")
            return

    msg = await update.message.reply_text("Fetching profiles...")

    try:
        netflix = netflix_sessions[user_id]["browser"]
        success, data = await netflix.get_profiles()

        if not success:
            await msg.edit_text(f"Failed: {data}")
            return

        all_profiles = data.get("profiles", [])
        regular_profiles = [p for p in all_profiles if not p.get("isKids", False)]
        kids_profiles = [p for p in all_profiles if p.get("isKids", False)]

        if kids_profiles:
            await msg.edit_text(
                f"Found {len(all_profiles)} profiles ({len(kids_profiles)} Kids - skipped)\n"
                f"Setting PINs for {len(regular_profiles)} regular profiles"
            )

        if len(pins) != len(regular_profiles):
            await msg.edit_text(
                f"Got {len(pins)} PINs but {len(regular_profiles)} regular profiles!\n"
                f"(Kids profiles: {len(kids_profiles)} - skipped)"
            )
            return

        await msg.edit_text(f"Setting {len(regular_profiles)} PINs in PARALLEL...")

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

        await msg.edit_text(text)

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
            await msg.edit_text(f"Error: {str(e)}")
        except:
            pass


async def addprofile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_authorized(user_id):
        await update.message.reply_text("Not authorized.")
        return

    if user_id not in netflix_sessions:
        await update.message.reply_text("Login first: /login <cookie>")
        return

    if not context.args:
        await update.message.reply_text("Usage: /addprofile <name>")
        return

    name = ' '.join(context.args)
    msg = await update.message.reply_text(f"Creating profile '{name}'...")

    netflix = netflix_sessions[user_id]["browser"]
    success, result = await netflix.add_profile(name)
    await msg.edit_text(f"{'OK' if success else 'FAIL'}: {result}")


async def updateprofile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_authorized(user_id):
        await update.message.reply_text("Not authorized.")
        return

    if user_id not in netflix_sessions:
        await update.message.reply_text("Login first: /login <cookie>")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Usage: /updateprofile <guid> <name>")
        return

    guid = context.args[0]
    name = ' '.join(context.args[1:])
    msg = await update.message.reply_text(f"Updating profile to '{name}'...")

    netflix = netflix_sessions[user_id]["browser"]
    success, result = await netflix.update_profile(guid, name)
    await msg.edit_text(f"{'OK' if success else 'FAIL'}: {result}")


async def deleteprofile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_authorized(user_id):
        await update.message.reply_text("Not authorized.")
        return

    if user_id not in netflix_sessions:
        await update.message.reply_text("Login first: /login <cookie>")
        return

    if not context.args:
        await update.message.reply_text("Usage: /deleteprofile <guid>")
        return

    guid = context.args[0]
    msg = await update.message.reply_text("Deleting profile...")

    netflix = netflix_sessions[user_id]["browser"]
    success, result = await netflix.delete_profile(guid)
    await msg.edit_text(f"{'OK' if success else 'FAIL'}: {result}")


async def setpin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_authorized(user_id):
        await update.message.reply_text("Not authorized.")
        return

    if user_id not in netflix_sessions:
        await update.message.reply_text("Login first: /login <cookie>")
        return

    if len(context.args) < 3:
        await update.message.reply_text("Usage: /setpin <guid> <pin> <password>")
        return

    guid, pin, password = context.args[0], context.args[1], context.args[2]

    if len(pin) != 4 or not pin.isdigit():
        await update.message.reply_text("PIN must be exactly 4 digits.")
        return

    msg = await update.message.reply_text("Setting PIN...")

    netflix = netflix_sessions[user_id]["browser"]
    success, result = await netflix.set_profile_pin(guid, pin, password)
    await msg.edit_text(f"{'OK' if success else 'FAIL'}: {result}")


async def adduser_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != HOST_USER_ID:
        await update.message.reply_text("Admin only.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /adduser <telegram_id>")
        return

    try:
        new_id = int(context.args[0])
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM authorized_users WHERE user_id = %s", (new_id,))
        if cur.fetchone():
            await update.message.reply_text(f"User {new_id} already authorized.")
            cur.close()
            conn.close()
            return

        cur.execute("INSERT INTO authorized_users (user_id, added_by) VALUES (%s, %s)", (new_id, user_id))
        conn.commit()
        cur.close()
        conn.close()
        await update.message.reply_text(f"User {new_id} authorized!")
    except ValueError:
        await update.message.reply_text("Invalid ID. Must be a number.")
    except Exception as e:
        logger.error(f"Add user error: {e}")
        await update.message.reply_text(f"Error: {str(e)}")


async def removeuser_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != HOST_USER_ID:
        await update.message.reply_text("Admin only.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /removeuser <telegram_id>")
        return

    try:
        remove_id = int(context.args[0])
        if remove_id == HOST_USER_ID:
            await update.message.reply_text("Can't remove the host user.")
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
            await update.message.reply_text(f"User {remove_id} removed.")
        else:
            await update.message.reply_text(f"User {remove_id} not found.")
    except ValueError:
        await update.message.reply_text("Invalid ID. Must be a number.")
    except Exception as e:
        logger.error(f"Remove user error: {e}")
        await update.message.reply_text(f"Error: {str(e)}")


async def listusers_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != HOST_USER_ID:
        await update.message.reply_text("Admin only.")
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
        await update.message.reply_text(msg, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"List users error: {e}")
        await update.message.reply_text(f"Error: {str(e)}")


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
