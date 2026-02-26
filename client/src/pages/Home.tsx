import { useLocation } from "wouter";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import HeroBanner from "../components/HeroBanner";
import ProductCard from "../components/ProductCard";
import { products, categories, dealProducts } from "../data/products";

function CategoryGrid() {
  const [, navigate] = useLocation();

  const categoryCards = [
    { title: "Gaming accessories", image: "https://picsum.photos/seed/gaming1/300/300", link: "/category/electronics" },
    { title: "Shop deals in Fashion", image: "https://picsum.photos/seed/fashion1/300/300", link: "/category/fashion" },
    { title: "Deals in PCs", image: "https://picsum.photos/seed/pc1/300/300", link: "/category/electronics" },
    { title: "Refresh your space", image: "https://picsum.photos/seed/home1/300/300", link: "/category/home-kitchen" },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
      {categoryCards.map((card) => (
        <div
          key={card.title}
          className="bg-white rounded-sm p-5 cursor-pointer hover:shadow-md transition-shadow"
          onClick={() => navigate(card.link)}
        >
          <h3 className="text-lg font-bold text-[#0F1111] mb-3">{card.title}</h3>
          <div className="aspect-[4/3] overflow-hidden rounded mb-3">
            <img
              src={card.image}
              alt={card.title}
              className="w-full h-full object-cover"
              loading="lazy"
            />
          </div>
          <span className="text-sm text-[#007185] hover:text-[#C7511F] hover:underline">
            Shop now
          </span>
        </div>
      ))}
    </div>
  );
}

function CategoryBrowse() {
  const [, navigate] = useLocation();

  return (
    <div className="bg-white rounded-sm p-5">
      <h2 className="text-xl font-bold text-[#0F1111] mb-4">Shop by Category</h2>
      <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-4">
        {categories.map((cat) => (
          <div
            key={cat.slug}
            className="flex flex-col items-center cursor-pointer group"
            onClick={() => navigate(`/category/${cat.slug}`)}
          >
            <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-full overflow-hidden border-2 border-transparent group-hover:border-[#007185] transition-colors mb-2">
              <img
                src={cat.image}
                alt={cat.name}
                className="w-full h-full object-cover"
                loading="lazy"
              />
            </div>
            <span className="text-xs sm:text-sm text-center text-[#0F1111] group-hover:text-[#C7511F]">
              {cat.name}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function DealSection() {
  return (
    <div className="bg-white rounded-sm p-5">
      <h2 className="text-xl font-bold text-[#0F1111] mb-4">Today's Deals</h2>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
        {dealProducts.slice(0, 6).map((product) => (
          <ProductCard key={product.id} product={product} />
        ))}
      </div>
    </div>
  );
}

function ProductSection({
  title,
  productList,
}: {
  title: string;
  productList: typeof products;
}) {
  return (
    <div className="bg-white rounded-sm p-5">
      <h2 className="text-xl font-bold text-[#0F1111] mb-4">{title}</h2>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
        {productList.map((product) => (
          <ProductCard key={product.id} product={product} />
        ))}
      </div>
    </div>
  );
}

function SignInBanner() {
  return (
    <div className="bg-white rounded-sm p-5 text-center">
      <h3 className="text-lg font-medium text-[#0F1111] mb-2">
        Sign in for the best experience
      </h3>
      <button className="amazon-btn-primary text-sm font-medium px-10 py-2">
        Sign in securely
      </button>
    </div>
  );
}

function PickUpWhereYouLeftOff() {
  const recommended = products.slice(0, 8);
  return (
    <div className="bg-white rounded-sm p-5">
      <h2 className="text-xl font-bold text-[#0F1111] mb-4">
        Inspired by your browsing history
      </h2>
      <div className="flex gap-4 overflow-x-auto pb-2 no-scrollbar">
        {recommended.map((product) => (
          <div key={product.id} className="min-w-[180px] max-w-[180px]">
            <ProductCard product={product} />
          </div>
        ))}
      </div>
    </div>
  );
}

function PopularBrands() {
  const brands = [
    { name: "Apple", img: "https://picsum.photos/seed/apple/150/80" },
    { name: "Samsung", img: "https://picsum.photos/seed/samsung/150/80" },
    { name: "Sony", img: "https://picsum.photos/seed/sony/150/80" },
    { name: "Nike", img: "https://picsum.photos/seed/nikebrand/150/80" },
    { name: "Dyson", img: "https://picsum.photos/seed/dysonbrand/150/80" },
    { name: "LEGO", img: "https://picsum.photos/seed/legobrand/150/80" },
  ];

  return (
    <div className="bg-white rounded-sm p-5">
      <h2 className="text-xl font-bold text-[#0F1111] mb-4">Popular Brands</h2>
      <div className="grid grid-cols-3 sm:grid-cols-6 gap-4">
        {brands.map((brand) => (
          <div
            key={brand.name}
            className="flex flex-col items-center gap-2 cursor-pointer group"
          >
            <div className="w-full aspect-[2/1] rounded bg-gray-100 overflow-hidden">
              <img
                src={brand.img}
                alt={brand.name}
                className="w-full h-full object-cover"
                loading="lazy"
              />
            </div>
            <span className="text-sm text-[#0F1111] group-hover:text-[#C7511F]">
              {brand.name}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Home() {
  const electronics = products.filter((p) => p.category === "Electronics").slice(0, 6);
  const homeKitchen = products.filter((p) => p.category === "Home & Kitchen").slice(0, 6);
  const bestSellers = products.filter((p) => p.badge === "Best Seller").slice(0, 6);

  return (
    <div className="min-h-screen bg-[#E3E6E6]">
      <Navbar />
      <main>
        <HeroBanner />
        <div className="max-w-[1500px] mx-auto px-3 -mt-48 sm:-mt-32 relative z-20 space-y-5 pb-8">
          <CategoryGrid />
          <SignInBanner />
          <DealSection />
          <CategoryBrowse />
          <PickUpWhereYouLeftOff />
          <ProductSection title="Best Sellers" productList={bestSellers} />
          <ProductSection title="Top picks in Electronics" productList={electronics} />
          <PopularBrands />
          <ProductSection title="Home & Kitchen favorites" productList={homeKitchen} />
        </div>
      </main>
      <Footer />
    </div>
  );
}
