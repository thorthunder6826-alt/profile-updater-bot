import { useLocation } from "wouter";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";

export default function NotFound() {
  const [, navigate] = useLocation();

  return (
    <div className="min-h-screen bg-[#E3E6E6]">
      <Navbar />
      <main className="max-w-[800px] mx-auto px-4 py-16 text-center">
        <div className="bg-white rounded-sm p-10">
          <h1 className="text-6xl font-bold text-[#232F3E] mb-4">404</h1>
          <p className="text-xl text-[#0F1111] mb-2">
            Looking for something?
          </p>
          <p className="text-sm text-[#565959] mb-6">
            We're sorry. The Web address you entered is not a functioning page on our site.
          </p>
          <button onClick={() => navigate("/")} className="amazon-btn-primary px-8 py-2.5">
            Go to Amazon's Home Page
          </button>
        </div>
      </main>
      <Footer />
    </div>
  );
}
