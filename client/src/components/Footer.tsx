import { useLocation } from "wouter";

export default function Footer() {
  const [, navigate] = useLocation();

  return (
    <footer>
      {/* Back to top */}
      <button
        onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
        className="w-full bg-[#37475A] hover:bg-[#485769] text-white text-sm py-3.5 cursor-pointer"
      >
        Back to top
      </button>

      {/* Main footer links */}
      <div className="bg-[#232F3E] text-white py-10">
        <div className="max-w-[1200px] mx-auto px-6 grid grid-cols-2 md:grid-cols-4 gap-8">
          <div>
            <h3 className="text-base font-bold mb-3">Get to Know Us</h3>
            <ul className="space-y-2 text-sm text-[#DDD]">
              <li className="hover:underline cursor-pointer">Careers</li>
              <li className="hover:underline cursor-pointer">Blog</li>
              <li className="hover:underline cursor-pointer">About Amazon</li>
              <li className="hover:underline cursor-pointer">Investor Relations</li>
              <li className="hover:underline cursor-pointer">Amazon Devices</li>
              <li className="hover:underline cursor-pointer">Amazon Science</li>
            </ul>
          </div>
          <div>
            <h3 className="text-base font-bold mb-3">Make Money with Us</h3>
            <ul className="space-y-2 text-sm text-[#DDD]">
              <li className="hover:underline cursor-pointer">Sell products on Amazon</li>
              <li className="hover:underline cursor-pointer">Sell on Amazon Business</li>
              <li className="hover:underline cursor-pointer">Sell apps on Amazon</li>
              <li className="hover:underline cursor-pointer">Become an Affiliate</li>
              <li className="hover:underline cursor-pointer">Advertise Your Products</li>
              <li className="hover:underline cursor-pointer">Self-Publish with Us</li>
            </ul>
          </div>
          <div>
            <h3 className="text-base font-bold mb-3">Amazon Payment Products</h3>
            <ul className="space-y-2 text-sm text-[#DDD]">
              <li className="hover:underline cursor-pointer">Amazon Business Card</li>
              <li className="hover:underline cursor-pointer">Shop with Points</li>
              <li className="hover:underline cursor-pointer">Reload Your Balance</li>
              <li className="hover:underline cursor-pointer">Amazon Currency Converter</li>
            </ul>
          </div>
          <div>
            <h3 className="text-base font-bold mb-3">Let Us Help You</h3>
            <ul className="space-y-2 text-sm text-[#DDD]">
              <li className="hover:underline cursor-pointer">Amazon and COVID-19</li>
              <li className="hover:underline cursor-pointer">Your Account</li>
              <li className="hover:underline cursor-pointer">Your Orders</li>
              <li className="hover:underline cursor-pointer">Shipping Rates & Policies</li>
              <li className="hover:underline cursor-pointer">Returns & Replacements</li>
              <li className="hover:underline cursor-pointer">Help</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Divider */}
      <div className="bg-[#232F3E] border-t border-[#3A4553]">
        <div className="max-w-[1200px] mx-auto px-6 py-6 flex flex-col items-center gap-3">
          <div
            className="cursor-pointer"
            onClick={() => navigate("/")}
          >
            <span className="text-xl font-bold text-white tracking-tight">
              amazon<span className="text-[#FF9900]">.com</span>
            </span>
          </div>
          <div className="flex gap-4 text-xs text-[#DDD]">
            <span className="hover:underline cursor-pointer">English</span>
            <span className="hover:underline cursor-pointer">USD - U.S. Dollar</span>
            <span className="hover:underline cursor-pointer">United States</span>
          </div>
        </div>
      </div>

      {/* Bottom bar */}
      <div className="bg-[#131A22] text-[#999] text-xs py-4">
        <div className="max-w-[1200px] mx-auto px-6 flex flex-wrap justify-center gap-x-4 gap-y-1">
          <span className="hover:underline cursor-pointer">Conditions of Use</span>
          <span className="hover:underline cursor-pointer">Privacy Notice</span>
          <span className="hover:underline cursor-pointer">Consumer Health Data Privacy Disclosure</span>
          <span className="hover:underline cursor-pointer">Your Ads Privacy Choices</span>
          <span>© 1996-2026, Amazon.com, Inc. or its affiliates</span>
        </div>
      </div>
    </footer>
  );
}
