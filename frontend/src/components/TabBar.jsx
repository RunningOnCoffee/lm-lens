export default function TabBar({ tabs, activeTab, onChange }) {
  return (
    <div className="flex border-b border-surface-600 mb-6">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onChange(tab.id)}
          className={`px-4 py-2.5 text-sm font-medium transition-colors relative ${
            activeTab === tab.id
              ? 'text-accent'
              : 'text-gray-500 hover:text-gray-300'
          }`}
        >
          {tab.label}
          {activeTab === tab.id && (
            <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-accent rounded-t" />
          )}
        </button>
      ))}
    </div>
  );
}
