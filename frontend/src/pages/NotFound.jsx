import { Link } from 'react-router-dom';

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
      <h1 className="text-6xl font-heading font-bold text-accent mb-2">404</h1>
      <p className="text-lg text-gray-400 mb-6">Page not found</p>
      <Link
        to="/"
        className="px-5 py-2.5 bg-accent/10 text-accent border border-accent/30 rounded-lg text-sm hover:bg-accent/20 transition-colors"
      >
        Back to Dashboard
      </Link>
    </div>
  );
}
