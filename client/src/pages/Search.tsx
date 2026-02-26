import { useLocation, useSearch } from "wouter";
import { useMemo, useState } from "react";
import { SlidersHorizontal, Grid3X3, List, Star } from "lucide-react";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import ProductCard, { StarRating } from "../components/ProductCard";
import { searchProducts } from "../data/products";

type SortOption = "featured" | "price-low" | "price-high" | "rating" | "reviews";

export default function Search() {
  const searchString = useSearch();
  const params = new URLSearchParams(searchString);
  const query = params.get("q") || "";
  const [, navigate] = useLocation();
  const [sortBy, setSortBy] = useState<SortOption>("featured");
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");

  const results = useMemo(() => {
    let items = searchProducts(query);
    switch (sortBy) {
      case "price-low":
        items.sort((a, b) => a.price - b.price);
        break;
      case "price-high":
        items.sort((a, b) => b.price - a.price);
        break;
      case "rating":
        items.sort((a, b) => b.rating - a.rating);
        break;
      case "reviews":
        items.sort((a, b) => b.reviewCount - a.reviewCount);
        break;
    }
    return items;
  }, [query, sortBy]);

  return (
    <div className="min-h-screen bg-[#E3E6E6]">
      <Navbar />
      <main className="max-w-[1500px] mx-auto px-4 py-4">
        {/* Results Header */}
        <div className="bg-white rounded-sm px-4 py-3 mb-4 flex items-center justify-between flex-wrap gap-2">
          <div className="text-sm text-[#565959]">
            <span className="font-bold text-[#C7511F]">{results.length}</span>{" "}
            results for{" "}
            <span className="font-bold text-[#0F1111]">"{query}"</span>
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

        {results.length === 0 ? (
          <div className="bg-white rounded-sm p-8 text-center">
            <h2 className="text-xl font-bold text-[#0F1111] mb-2">
              No results found for "{query}"
            </h2>
            <p className="text-sm text-[#565959] mb-4">
              Try checking your spelling or use more general terms
            </p>
            <button
              onClick={() => navigate("/")}
              className="amazon-btn-primary"
            >
              Back to Home
            </button>
          </div>
        ) : viewMode === "grid" ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
            {results.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
        ) : (
          <div className="space-y-4">
            {results.map((product) => {
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
                        <span className="text-xs font-bold text-[#007185]">prime</span>
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
      </main>
      <Footer />
    </div>
  );
}
