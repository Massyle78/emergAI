import { Link } from "react-router-dom";

export function NotFound() {
  return (
    <div className="flex flex-1 items-center justify-center p-6">
      <div className="text-center">
        <p className="text-6xl font-bold text-primary-600">404</p>
        <h1 className="mt-4 text-2xl font-semibold text-slate-900">
          Page not found
        </h1>
        <p className="mt-2 text-slate-500">
          The page you're looking for doesn't exist or has been moved.
        </p>
        <Link to="/" className="kiosk-btn-secondary mt-6 inline-flex">
          Back to Home
        </Link>
      </div>
    </div>
  );
}
