import { useParams, useLocation } from "wouter";
import { useState } from "react";
import {
  Star,
  Heart,
  Share2,
  ShieldCheck,
  Truck,
  RotateCcw,
  MapPin,
  Check,
} from "lucide-react";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import ProductCard, { StarRating } from "../components/ProductCard";
import { getProductById, products } from "../data/products";
import { useCart } from "../context/CartContext";

export default function ProductDetail() {
  const { id } = useParams<{ id: string }>();
  const [, navigate] = useLocation();
  const { addToCart } = useCart();
  const [quantity, setQuantity] = useState(1);
  const [addedToCart, setAddedToCart] = useState(false);

  const product = getProductById(Number(id));

  if (!product) {
    return (
      <div className="min-h-screen bg-[#E3E6E6]">
        <Navbar />
        <div className="max-w-[1200px] mx-auto p-8 text-center">
          <h1 className="text-2xl font-bold mb-4">Product not found</h1>
          <button onClick={() => navigate("/")} className="amazon-btn-primary">
            Go to Homepage
          </button>
        </div>
        <Footer />
      </div>
    );
  }

  const discount = product.originalPrice
    ? Math.round(
        ((product.originalPrice - product.price) / product.originalPrice) * 100
      )
    : 0;

  const relatedProducts = products
    .filter((p) => p.category === product.category && p.id !== product.id)
    .slice(0, 6);

  const handleAddToCart = () => {
    addToCart(product, quantity);
    setAddedToCart(true);
    setTimeout(() => setAddedToCart(false), 2000);
  };

  return (
    <div className="min-h-screen bg-white">
      <Navbar />
      <main className="max-w-[1500px] mx-auto px-4 py-4">
        {/* Breadcrumb */}
        <nav className="text-sm text-[#007185] mb-4 flex gap-1 flex-wrap">
          <span
            className="hover:text-[#C7511F] hover:underline cursor-pointer"
            onClick={() => navigate("/")}
          >
            Home
          </span>
          <span className="text-[#565959]">›</span>
          <span
            className="hover:text-[#C7511F] hover:underline cursor-pointer"
            onClick={() =>
              navigate(
                `/category/${product.category.toLowerCase().replace(/ & /g, "-").replace(/ /g, "-")}`
              )
            }
          >
            {product.category}
          </span>
          <span className="text-[#565959]">›</span>
          <span className="text-[#565959]">{product.subcategory}</span>
        </nav>

        {/* Product Detail Grid */}
        <div className="grid grid-cols-1 md:grid-cols-[1fr_1fr_300px] gap-6">
          {/* Image Column */}
          <div className="flex flex-col items-center">
            <div className="sticky top-32 w-full max-w-[450px] aspect-square rounded-lg overflow-hidden bg-white border border-gray-200 flex items-center justify-center p-4">
              <img
                src={product.image}
                alt={product.title}
                className="max-w-full max-h-full object-contain"
              />
            </div>
          </div>

          {/* Info Column */}
          <div className="space-y-3">
            <h1 className="text-xl sm:text-2xl font-medium text-[#0F1111] leading-tight">
              {product.title}
            </h1>

            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm text-[#007185]">
                Visit the {product.seller} Store
              </span>
            </div>

            <div className="flex items-center gap-3">
              <span className="text-sm font-medium text-[#0F1111]">
                {product.rating}
              </span>
              <StarRating rating={product.rating} count={product.reviewCount} />
            </div>

            <hr className="border-gray-200" />

            {/* Price Block */}
            <div>
              {discount > 0 && (
                <div className="flex items-center gap-2 mb-1">
                  <span className="deal-badge">-{discount}%</span>
                  <div className="flex items-baseline">
                    <span className="text-sm align-top">$</span>
                    <span className="text-[28px] font-medium text-[#0F1111]">
                      {Math.floor(product.price)}
                    </span>
                    <span className="text-sm align-top">
                      {(product.price % 1).toFixed(2).slice(1)}
                    </span>
                  </div>
                </div>
              )}
              {!discount && (
                <div className="flex items-baseline mb-1">
                  <span className="text-sm align-top">$</span>
                  <span className="text-[28px] font-medium text-[#0F1111]">
                    {Math.floor(product.price)}
                  </span>
                  <span className="text-sm align-top">
                    {(product.price % 1).toFixed(2).slice(1)}
                  </span>
                </div>
              )}
              {product.originalPrice && (
                <div className="text-sm text-[#565959]">
                  List Price:{" "}
                  <span className="line-through">
                    ${product.originalPrice.toFixed(2)}
                  </span>
                </div>
              )}
            </div>

            {product.isPrime && (
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold text-[#007185]">prime</span>
                <span className="text-sm text-[#565959]">
                  FREE delivery{" "}
                  <span className="font-bold text-[#0F1111]">Tomorrow</span>
                </span>
              </div>
            )}

            <hr className="border-gray-200" />

            {/* Description */}
            <div>
              <h3 className="text-base font-bold text-[#0F1111] mb-2">
                About this item
              </h3>
              <p className="text-sm text-[#333] mb-3">{product.description}</p>
              <ul className="space-y-1.5">
                {product.features.map((feature, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-[#333]">
                    <span className="text-[#0F1111] mt-0.5 shrink-0">•</span>
                    {feature}
                  </li>
                ))}
              </ul>
            </div>

            <hr className="border-gray-200" />

            {/* Additional Info */}
            <div className="grid grid-cols-2 gap-y-2 text-sm">
              <span className="text-[#565959] font-bold">Brand</span>
              <span className="text-[#0F1111]">{product.seller}</span>
              <span className="text-[#565959] font-bold">Category</span>
              <span className="text-[#0F1111]">{product.category}</span>
              <span className="text-[#565959] font-bold">Subcategory</span>
              <span className="text-[#0F1111]">{product.subcategory}</span>
            </div>
          </div>

          {/* Buy Box Column */}
          <div className="md:sticky md:top-32 self-start">
            <div className="border border-[#D5D9D9] rounded-lg p-5 space-y-3">
              <div className="flex items-baseline">
                <span className="text-sm align-top">$</span>
                <span className="text-[22px] font-medium text-[#0F1111]">
                  {Math.floor(product.price)}
                </span>
                <span className="text-sm align-top">
                  {(product.price % 1).toFixed(2).slice(1)}
                </span>
              </div>

              {product.isPrime && (
                <div className="text-sm">
                  <span className="font-bold text-[#007185]">prime</span>{" "}
                  <span className="text-[#565959]">FREE delivery</span>
                  <div className="font-bold text-[#0F1111]">Tomorrow, Feb 27</div>
                </div>
              )}

              <div className="flex items-center gap-1 text-sm">
                <MapPin size={14} className="text-[#565959]" />
                <span className="text-[#007185]">Deliver to United States</span>
              </div>

              <div className="text-lg font-medium text-[#007600]">
                {product.inStock ? "In Stock" : "Out of Stock"}
              </div>

              {/* Quantity */}
              <div className="flex items-center gap-2">
                <span className="text-sm">Qty:</span>
                <select
                  value={quantity}
                  onChange={(e) => setQuantity(Number(e.target.value))}
                  className="border border-[#D5D9D9] rounded-lg bg-[#F0F2F2] px-2 py-1 text-sm shadow-sm"
                >
                  {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </select>
              </div>

              <button
                onClick={handleAddToCart}
                className="w-full amazon-btn-primary py-2.5"
              >
                {addedToCart ? (
                  <span className="flex items-center justify-center gap-1">
                    <Check size={16} /> Added to Cart
                  </span>
                ) : (
                  "Add to Cart"
                )}
              </button>

              <button
                onClick={() => {
                  addToCart(product, quantity);
                  navigate("/cart");
                }}
                className="w-full amazon-btn-orange py-2.5"
              >
                Buy Now
              </button>

              {/* Secure */}
              <div className="space-y-2 text-xs text-[#565959]">
                <div className="flex items-center gap-2">
                  <ShieldCheck size={16} />
                  <span>Secure transaction</span>
                </div>
                <div className="flex items-center gap-2">
                  <Truck size={16} />
                  <span>Ships from Amazon</span>
                </div>
                <div className="flex items-center gap-2">
                  <RotateCcw size={16} />
                  <span>Eligible for Return, Refund or Replacement</span>
                </div>
              </div>

              <hr className="border-gray-200" />

              {/* Actions */}
              <div className="flex gap-4 text-sm">
                <button className="flex items-center gap-1 text-[#007185] hover:text-[#C7511F] hover:underline">
                  <Heart size={14} /> Add to List
                </button>
                <button className="flex items-center gap-1 text-[#007185] hover:text-[#C7511F] hover:underline">
                  <Share2 size={14} /> Share
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Related Products */}
        {relatedProducts.length > 0 && (
          <div className="mt-10 border-t border-gray-200 pt-6">
            <h2 className="text-xl font-bold text-[#0F1111] mb-4">
              Products related to this item
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
              {relatedProducts.map((p) => (
                <ProductCard key={p.id} product={p} />
              ))}
            </div>
          </div>
        )}
      </main>
      <Footer />
    </div>
  );
}
