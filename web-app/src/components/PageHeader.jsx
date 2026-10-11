import React from 'react';

export default function PageHeader({ icon: Icon, title, description, badge, children }) {
  return (
    <header className="page-head">
      {Icon && (
        <div className="icon-tile">
          <Icon size={24} aria-hidden="true" />
        </div>
      )}
      <div className="flex-1 min-w-0">
        <h2 className="page-title">
          {title}
          {badge}
        </h2>
        {description && <p className="muted text-sm mt-1 max-w-2xl">{description}</p>}
      </div>
      {children}
    </header>
  );
}
