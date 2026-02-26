import { useLocation } from "wouter";
import { Trash2, ShieldCheck } from "lucide-react";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import ProductCard from "../components/ProductCard";
import { useCart } from "../context/CartContext";
import { products } from "../data/products";

export default function Cart() {
  const { items, removeFromCart, updateQuantity, totalPrice, totalItems } = useCart();
  const [, navigate] = useLocation();

  const recommended = products.slice(8, 14);

  if (items.length === 0) {
    return (
      <div className="min-h-screen bg-[#E3E6E6]">
        <Navbar />
        <main className="max-w-[1200px] mx-auto px-4 py-8">
          <div className="bg-white rounded-sm p-8 flex flex-col sm:flex-row gap-6 items-center sm:items-start">
            <div className="text-8xl">🛒</div>
            <div>
              <h1 className="text-[28px] font-bold text-[#0F1111] mb-2">
                Your Amazon Cart is empty
              </h1>
              <p className="text-sm text-[#565959] mb-4">
                Your Shopping Cart lives to serve. Give it purpose — fill it with
                groceries, clothing, household supplies, electronics, and more.
              </p>
              <button
                onClick={() => navigate("/")}
                className="amazon-btn-primary px-6"
              >
                Continue shopping
              </button>
            </div>
          </div>

          {/* Recommended */}
          <div className="bg-white rounded-sm p-5 mt-5">
            <h2 className="text-xl font-bold text-[#0F1111] mb-4">
              Recommended for you
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
              {recommended.map((p) => (
                <ProductCard key={p.id} product={p} />
              ))}
            </div>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#E3E6E6]">
      <Navbar />
      <main className="max-w-[1200px] mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-5">
          {/* Cart Items */}
          <div className="bg-white rounded-sm p-5">
            <h1 className="text-[28px] font-bold text-[#0F1111] mb-1">
              Shopping Cart
            </h1>
            <div className="text-right text-sm text-[#565959] mb-2">Price</div>
            <hr className="border-gray-200 mb-4" />

            <div className="space-y-4">
              {items.map(({ product, quantity }) => {
                const discount = product.originalPrice
                  ? Math.round(
                      ((product.originalPrice - product.price) /
                        product.originalPrice) *
                        100
                    )
                  : 0;

                return (
                  <div key={product.id}>
                    <div className="flex gap-4">
                      {/* Image */}
                      <div
                        className="w-[180px] h-[180px] shrink-0 cursor-pointer flex items-center justify-center"
                        onClick={() => navigate(`/product/${product.id}`)}
                      >
                        <img
                          src={product.image}
                          alt={product.title}
                          className="max-w-full max-h-full object-contain"
                        />
                      </div>

                      {/* Details */}
                      <div className="flex-1 min-w-0">
                        <h3
                          className="text-base font-medium text-[#0F1111] leading-tight cursor-pointer hover:text-[#C7511F] line-clamp-2"
                          onClick={() => navigate(`/product/${product.id}`)}
                        >
                          {product.title}
                        </h3>

                        <div className="text-sm text-[#007600] mt-1">In Stock</div>

                        {product.isPrime && (
                          <div className="flex items-center gap-1 mt-1">
                            <span className="text-xs font-bold text-[#007185]">
                              prime
                            </span>
                            <span className="text-xs text-[#565959]">
                              FREE Delivery
                            </span>
                          </div>
                        )}

                        <div className="text-xs text-[#565959] mt-1">
                          Sold by: {product.seller}
                        </div>

                        {/* Actions */}
                        <div className="flex items-center gap-3 mt-3 flex-wrap">
                          <select
                            value={quantity}
                            onChange={(e) =>
                              updateQuantity(product.id, Number(e.target.value))
                            }
                            className="border border-[#D5D9D9] rounded-lg bg-[#F0F2F2] px-2 py-1 text-sm shadow-sm"
                          >
                            {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((n) => (
                              <option key={n} value={n}>
                                Qty: {n}
                              </option>
                            ))}
                          </select>

                          <span className="text-[#D5D9D9]">|</span>

                          <button
                            onClick={() => removeFromCart(product.id)}
                            className="flex items-center gap-1 text-sm text-[#007185] hover:text-[#C7511F] hover:underline"
                          >
                            <Trash2 size={14} /> Delete
                          </button>

                          <span className="text-[#D5D9D9]">|</span>

                          <button className="text-sm text-[#007185] hover:text-[#C7511F] hover:underline">
                            Save for later
                          </button>
                        </div>
                      </div>

                      {/* Price */}
                      <div className="text-right shrink-0">
                        <div className="text-lg font-bold text-[#0F1111]">
                          ${(product.price * quantity).toFixed(2)}
                        </div>
                        {discount > 0 && product.originalPrice && (
                          <>
                            <div className="text-xs text-[#565959] line-through">
                              ${(product.originalPrice * quantity).toFixed(2)}
                            </div>
                            <span className="deal-badge">{discount}% off</span>
                          </>
                        )}
                      </div>
                    </div>
                    <hr className="border-gray-200 mt-4" />
                  </div>
                );
              })}
            </div>

            {/* Subtotal */}
            <div className="text-right mt-4 text-lg">
              Subtotal ({totalItems} {totalItems === 1 ? "item" : "items"}):{" "}
              <span className="font-bold text-[#0F1111]">
                ${totalPrice.toFixed(2)}
              </span>
            </div>
          </div>

          {/* Checkout Box */}
          <div className="self-start">
            <div className="bg-white rounded-sm p-5 space-y-3 sticky top-32">
              <div className="flex items-center gap-1 text-sm text-[#067D62]">
                <ShieldCheck size={16} />
                Your order qualifies for FREE Shipping.
              </div>

              <div className="text-lg">
                Subtotal ({totalItems} {totalItems === 1 ? "item" : "items"}):{" "}
                <span className="font-bold text-[#0F1111]">
                  ${totalPrice.toFixed(2)}
                </span>
              </div>

              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" className="rounded" />
                This order contains a gift
              </label>

              <button className="w-full amazon-btn-primary py-2.5">
                Proceed to checkout
              </button>
            </div>
          </div>
        </div>

        {/* Recommended */}
        <div className="bg-white rounded-sm p-5 mt-5">
          <h2 className="text-xl font-bold text-[#0F1111] mb-4">
            Customers who bought items in your cart also bought
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {recommended.map((p) => (
              <ProductCard key={p.id} product={p} />
            ))}
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
