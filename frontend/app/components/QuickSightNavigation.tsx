import Link from 'next/link';
import { usePathname } from 'next/navigation';

const QuickSightNavigation = () => {
  const pathname = usePathname();

  const navItems = [
    { href: '/analytics', label: 'Analytics Dashboard', icon: '📊' },
    { href: '/quicksight-status', label: 'QuickSight Status', icon: '🔍' },
    { href: '/test-quicksight', label: 'Integration Test', icon: '🧪' },
  ];

  return (
    <nav className="bg-white shadow-sm border-b">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex space-x-8">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                pathname === item.href
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <span className="mr-2">{item.icon}</span>
              {item.label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
};

export default QuickSightNavigation;