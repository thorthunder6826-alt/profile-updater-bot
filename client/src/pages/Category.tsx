import { useParams, useLocation } from "wouter";
import { useState, useMemo } from "react";
import { SlidersHorizontal, ChevronDown, Star, Grid3X3, List } from "lucide-react";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import ProductCard, { StarRating } from "../components/ProductCard";
import { categories, products } from "../data/products";

type SortOption = "featured" | "price-low" | "price-high" | "rating" | "reviews";

export default function Category() {
  const { slug } = useParams<{ slug: string }>();
  const [, navigate] = useLocation();
  const [sortBy, setSortBy] = useState<SortOption>("featured");
  const [priceRange, setPriceRange] = useState<[number, number]>([0, 10000]);
  const [selectedRating, setSelectedRating] = useState(0);
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");

  const category = categories.find((c) => c.slug === slug);
  const categoryName = category?.name || slug?.replace(/-/g, " ") || "";

  const filteredProducts = useMemo(() => {
    let filtered = products.filter(
      (p) => p.category.toLowerCase() === categoryName.toLowerCase()
    );

    if (selectedRating > 0) {
      filtered = filtered.filter((p) => p.rating >= selectedRating);
    }

    filtered = filtered.filter(
      (p) => p.price >= priceRange[0] && p.price <= priceRange[1]
    );

    switch (sortBy) {
      case "price-low":
        filtered.sort((a, b) => a.price - b.price);
        break;
      case "price-high":
        filtered.sort((a, b) => b.price - a.price);
        break;
      case "rating":
        filtered.sort((a, b) => b.rating - a.rating);
        break;
      case "reviews":
        filtered.sort((a, b) => b.reviewCount - a.reviewCount);
        break;
    }

    return filtered;
  }, [categoryName, sortBy, selectedRating, priceRange]);

  return (
    <div className="min-h-screen bg-[#E3E6E6]">
      <Navbar />
      <main className="max-w-[1500px] mx-auto px-4 py-4">
        {/* Breadcrumb */}
        <nav className="text-sm text-[#007185] mb-4 flex gap-1">
          <span
            className="hover:text-[#C7511F] hover:underline cursor-pointer"
            onClick={() => navigate("/")}
          >
            Home
          </span>
          <span className="text-[#565959]">›</span>
          <span className="text-[#565959] capitalize">{categoryName}</span>
        </nav>

        <div className="grid grid-cols-1 lg:grid-cols-[220px_1fr] gap-4">
          {/* Sidebar Filters */}
          <aside className="space-y-5">
            <div className="bg-white rounded-sm p-4">
              <h3 className="font-bold text-[#0F1111] mb-3">Department</h3>
              <ul className="space-y-1.5 text-sm">
                <li className="font-bold text-[#0F1111]">{categoryName}</li>
                {category?.subcategories.map((sub) => (
                  <li
                    key={sub}
                    className="text-[#0F1111] pl-3 hover:text-[#C7511F] cursor-pointer"
                  >
                    {sub}
                  </li>
                ))}
              </ul>
            </div>

            <div className="bg-white rounded-sm p-4">
              <h3 className="font-bold text-[#0F1111] mb-3">Customer Review</h3>
              <div className="space-y-1.5">
                {[4, 3, 2, 1].map((rating) => (
                  <button
                    key={rating}
                    onClick={() =>
                      setSelectedRating(selectedRating === rating ? 0 : rating)
                    }
                    className={`flex items-center gap-1 text-sm w-full hover:text-[#C7511F] ${
                      selectedRating === rating ? "font-bold" : ""
                    }`}
                  >
                    <div className="flex">
                      {[1, 2, 3, 4, 5].map((i) => (
                        <Star
                          key={i}
                          size={14}
                          className={
                            i <= rating
                              ? "fill-[#FFA41C] text-[#FFA41C]"
                              : "text-gray-300"
                          }
                        />
                      ))}
                    </div>
                    <span>& Up</span>
                  </button>
                ))}
              </div>
            </div>

            <div className="bg-white rounded-sm p-4">
              <h3 className="font-bold text-[#0F1111] mb-3">Price</h3>
              <ul className="space-y-1.5 text-sm text-[#0F1111]">
                {[
                  [0, 25],
                  [25, 50],
                  [50, 100],
                  [100, 200],
                  [200, 500],
                  [500, 10000],
                ].map(([min, max]) => (
                  <li
                    key={`${min}-${max}`}
                    className="hover:text-[#C7511F] cursor-pointer"
                    onClick={() => setPriceRange([min, max])}
                  >
                    {max === 10000 ? `$${min} & Above` : `$${min} to $${max}`}
                  </li>
                ))}
                <li
                  className="hover:text-[#C7511F] cursor-pointer text-[#007185]"
                  onClick={() => setPriceRange([0, 10000])}
                >
                  Clear
                </li>
              </ul>
            </div>

            <div className="bg-white rounded-sm p-4">
              <h3 className="font-bold text-[#0F1111] mb-3">Availability</h3>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" defaultChecked className="rounded" />
                Include Out of Stock
              </label>
            </div>
          </aside>

          {/* Product Grid */}
          <div>
            {/* Results Header */}
            <div className="bg-white rounded-sm px-4 py-3 mb-4 flex items-center justify-between flex-wrap gap-2">
              <div className="text-sm text-[#565959]">
                <span className="font-bold text-[#C7511F]">
                  {filteredProducts.length}
                </span>{" "}
                results for{" "}
                <span className="font-bold text-[#0F1111]">"{categoryName}"</span>
              </div>

              <div className="flex items-center gap-3">
                <div className="flex border border-[#D5D9D9] rounded overflow-hidden">
                  <button
                    onClick={() => setViewMode("grid")}
                    className={`p-1.5 ${viewMode === "grid" ? "bg-[#E7E9EC]" : "hover:bg-[#F7FAFA]"}`}
                  >
                    <Grid3X3 size={16} />
                  </button>
                  <button
                    onClick={() => setViewMode("list")}
                    className={`p-1.5 ${viewMode === "list" ? "bg-[#E7E9EC]" : "hover:bg-[#F7FAFA]"}`}
                  >
                    <List size={16} />
                  </button>
                </div>

                <div className="flex items-center gap-1">
                  <SlidersHorizontal size={14} className="text-[#565959]" />
                  <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value as SortOption)}
                    className="border border-[#D5D9D9] rounded bg-[#F0F2F2] px-2 py-1 text-sm shadow-sm"
                  >
                    <option value="featured">Featured</option>
                    <option value="price-low">Price: Low to High</option>
                    <option value="price-high">Price: High to Low</option>
                    <option value="rating">Avg. Customer Review</option>
                    <option value="reviews">Most Reviews</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Products */}
            {filteredProducts.length === 0 ? (
              <div className="bg-white rounded-sm p-8 text-center">
                <h2 className="text-xl font-bold text-[#0F1111] mb-2">
                  No results found
                </h2>
                <p className="text-sm text-[#565959]">
                  Try adjusting your filters or browse other categories.
                </p>
              </div>
            ) : viewMode === "grid" ? (
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
                {filteredProducts.map((product) => (
                  <ProductCard key={product.id} product={product} />
                ))}
              </div>
            ) : (
              <div className="space-y-4">
                {filteredProducts.map((product) => {
                  const discount = product.originalPrice
                    ? Math.round(
                        ((product.originalPrice - product.price) /
                          product.originalPrice) *
                          100
                      )
                    : 0;

                  return (
                    <div
                      key={product.id}
                      className="bg-white rounded-sm p-4 flex gap-4 cursor-pointer hover:shadow-md transition-shadow"
                      onClick={() => navigate(`/product/${product.id}`)}
                    >
                      <div className="w-[200px] h-[200px] shrink-0 flex items-center justify-center">
                        <img
                          src={product.image}
                          alt={product.title}
                          className="max-w-full max-h-full object-contain"
                          loading="lazy"
                        />
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="text-base font-medium text-[#0F1111] leading-tight hover:text-[#C7511F] line-clamp-2 mb-1">
                          {product.title}
                        </h3>
                        <StarRating
                          rating={product.rating}
                          count={product.reviewCount}
                        />
                        <div className="mt-2">
                          {discount > 0 && (
                            <span className="deal-badge mr-2">{discount}% off</span>
                          )}
                          <div className="flex items-baseline gap-1">
                            <span className="text-xs align-top">$</span>
                            <span className="text-xl font-medium text-[#0F1111]">
                              {Math.floor(product.price)}
                            </span>
                            <span className="text-xs align-top">
                              {(product.price % 1).toFixed(2).slice(1)}
                            </span>
                            {product.originalPrice && (
                              <span className="text-xs text-[#565959] line-through ml-2">
                                ${product.originalPrice.toFixed(2)}
                              </span>
                            )}
                          </div>
                        </div>
                        {product.isPrime && (
                          <div className="flex items-center gap-1 mt-1">
                            <span className="text-xs font-bold text-[#007185]">
                              prime
                            </span>
                            <span className="text-xs text-[#565959]">
                              FREE Delivery Tomorrow
                            </span>
                          </div>
                        )}
                        <p className="text-sm text-[#565959] mt-2 line-clamp-2">
                          {product.description}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
