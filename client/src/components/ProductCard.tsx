import { useLocation } from "wouter";
import { Star } from "lucide-react";
import type { Product } from "../data/products";

function StarRating({ rating, count }: { rating: number; count: number }) {
  return (
    <div className="flex items-center gap-1">
      <div className="flex">
        {[1, 2, 3, 4, 5].map((i) => (
          <Star
            key={i}
            size={14}
            className={
              i <= Math.floor(rating)
                ? "fill-[#FFA41C] text-[#FFA41C]"
                : i - 0.5 <= rating
                ? "fill-[#FFA41C]/50 text-[#FFA41C]"
                : "text-gray-300"
            }
          />
        ))}
      </div>
      <span className="text-xs text-[#007185] hover:text-[#C7511F] cursor-pointer">
        {count.toLocaleString()}
      </span>
    </div>
  );
}

export { StarRating };

export default function ProductCard({ product }: { product: Product }) {
  const [, navigate] = useLocation();
  const discount = product.originalPrice
    ? Math.round(((product.originalPrice - product.price) / product.originalPrice) * 100)
    : 0;

  return (
    <div
      className="bg-white rounded-sm p-4 cursor-pointer group hover:shadow-md transition-shadow flex flex-col"
      onClick={() => navigate(`/product/${product.id}`)}
    >
      {/* Badge */}
      {product.badge && (
        <div className="mb-2">
          {product.badge === "Best Seller" && (
            <span className="bg-[#E77600] text-white text-xs font-bold px-2 py-0.5 rounded-sm">
              Best Seller
            </span>
          )}
          {product.badge === "Amazon's Choice" && (
            <span className="bg-[#232F3E] text-white text-xs font-bold px-2 py-0.5 rounded-sm">
              Amazon's <span className="text-[#F69931]">Choice</span>
            </span>
          )}
          {product.badge === "Limited Deal" && (
            <span className="deal-badge">Limited time deal</span>
          )}
        </div>
      )}

      {/* Image */}
      <div className="relative w-full aspect-square mb-3 overflow-hidden rounded flex items-center justify-center bg-white">
        <img
          src={product.image}
          alt={product.title}
          className="max-w-full max-h-full object-contain group-hover:scale-105 transition-transform duration-200"
          loading="lazy"
        />
      </div>

      {/* Title */}
      <h3 className="text-sm text-[#0F1111] leading-tight line-clamp-2 group-hover:text-[#C7511F] mb-1">
        {product.title}
      </h3>

      {/* Rating */}
      <StarRating rating={product.rating} count={product.reviewCount} />

      {/* Price */}
      <div className="mt-1">
        {discount > 0 && (
          <div className="flex items-center gap-2">
            <span className="deal-badge">{discount}% off</span>
          </div>
        )}
        <div className="flex items-baseline gap-1 mt-0.5">
          <span className="text-xs align-top">$</span>
          <span className="text-xl font-medium text-[#0F1111]">
            {Math.floor(product.price)}
          </span>
          <span className="text-xs align-top">
            {(product.price % 1).toFixed(2).slice(1)}
          </span>
        </div>
        {product.originalPrice && (
          <span className="text-xs text-[#565959] line-through">
            ${product.originalPrice.toFixed(2)}
          </span>
        )}
      </div>

      {/* Prime */}
      {product.isPrime && (
        <div className="mt-1 flex items-center gap-1">
          <span className="text-xs font-bold text-[#007185]">prime</span>
          <span className="text-xs text-[#565959]">FREE Delivery</span>
        </div>
      )}
    </div>
  );
}
