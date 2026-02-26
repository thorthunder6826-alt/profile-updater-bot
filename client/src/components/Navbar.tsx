import { useState } from "react";
import { useLocation } from "wouter";
import { Search, MapPin, ShoppingCart, ChevronDown, Menu } from "lucide-react";
import { useCart } from "../context/CartContext";
import { categories } from "../data/products";

export default function Navbar() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("All");
  const [, navigate] = useLocation();
  const { totalItems } = useCart();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/search?q=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

  return (
    <header className="sticky top-0 z-50">
      {/* Main Navbar */}
      <div className="bg-[#131921] text-white">
        <div className="max-w-[1500px] mx-auto flex items-center gap-2 px-2 py-2">
          {/* Logo */}
          <div
            className="flex items-center px-2 py-1.5 border border-transparent hover:border-white rounded cursor-pointer shrink-0"
            onClick={() => navigate("/")}
          >
            <span className="text-xl font-bold tracking-tight">
              amazon<span className="text-[#FF9900]">.com</span>
            </span>
          </div>

          {/* Deliver to */}
          <div className="hidden md:flex items-center px-2 py-1.5 border border-transparent hover:border-white rounded cursor-pointer shrink-0">
            <MapPin size={18} className="text-white mr-1" />
            <div className="leading-tight">
              <span className="text-[#ccc] text-xs block">Deliver to</span>
              <span className="text-sm font-bold">United States</span>
            </div>
          </div>

          {/* Search Bar */}
          <form onSubmit={handleSearch} className="flex flex-1 h-10">
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="hidden sm:block bg-[#e6e6e6] text-[#555] text-xs rounded-l-md px-2 border-none outline-none cursor-pointer hover:bg-[#d4d4d4]"
            >
              <option value="All">All</option>
              {categories.map((cat) => (
                <option key={cat.slug} value={cat.name}>
                  {cat.name}
                </option>
              ))}
            </select>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search Amazon"
              className="flex-1 px-3 text-black text-sm outline-none border-none sm:rounded-none rounded-l-md"
            />
            <button
              type="submit"
              className="bg-[#FEBD69] hover:bg-[#F3A847] px-3 rounded-r-md flex items-center justify-center"
            >
              <Search size={22} className="text-[#131921]" />
            </button>
          </form>

          {/* Language */}
          <div className="hidden lg:flex items-center px-2 py-1.5 border border-transparent hover:border-white rounded cursor-pointer shrink-0">
            <img
              src="https://flagcdn.com/w20/us.png"
              alt="US"
              className="w-5 mr-1"
            />
            <span className="text-sm font-bold">EN</span>
            <ChevronDown size={12} className="text-[#ccc] ml-0.5" />
          </div>

          {/* Account */}
          <div className="hidden sm:flex flex-col px-2 py-1.5 border border-transparent hover:border-white rounded cursor-pointer shrink-0">
            <span className="text-xs text-[#ccc]">Hello, sign in</span>
            <span className="text-sm font-bold flex items-center">
              Account & Lists <ChevronDown size={12} className="ml-0.5" />
            </span>
          </div>

          {/* Returns */}
          <div className="hidden sm:flex flex-col px-2 py-1.5 border border-transparent hover:border-white rounded cursor-pointer shrink-0">
            <span className="text-xs text-[#ccc]">Returns</span>
            <span className="text-sm font-bold">& Orders</span>
          </div>

          {/* Cart */}
          <div
            className="flex items-center px-2 py-1.5 border border-transparent hover:border-white rounded cursor-pointer shrink-0"
            onClick={() => navigate("/cart")}
          >
            <div className="relative">
              <ShoppingCart size={28} />
              <span className="absolute -top-1 left-3 bg-[#F08804] text-[#131921] text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center">
                {totalItems}
              </span>
            </div>
            <span className="text-sm font-bold ml-1 hidden sm:block">Cart</span>
          </div>
        </div>
      </div>

      {/* Sub Navbar */}
      <div className="bg-[#232F3E] text-white">
        <div className="max-w-[1500px] mx-auto flex items-center gap-0.5 px-1 text-sm overflow-x-auto no-scrollbar">
          <div className="flex items-center px-2 py-1.5 hover:border hover:border-white rounded cursor-pointer whitespace-nowrap border border-transparent">
            <Menu size={18} className="mr-1" />
            <span className="font-bold">All</span>
          </div>
          {["Today's Deals", "Customer Service", "Registry", "Gift Cards", "Sell"].map(
            (item) => (
              <div
                key={item}
                className="px-2 py-1.5 hover:border hover:border-white rounded cursor-pointer whitespace-nowrap border border-transparent"
              >
                {item}
              </div>
            )
          )}
          {categories.slice(0, 4).map((cat) => (
            <div
              key={cat.slug}
              className="px-2 py-1.5 hover:border hover:border-white rounded cursor-pointer whitespace-nowrap border border-transparent"
              onClick={() => navigate(`/category/${cat.slug}`)}
            >
              {cat.name}
            </div>
          ))}
        </div>
      </div>
    </header>
  );
}
