import React from 'react';

/**
 * Header component for the application.
 * Displays the application title and provides a consistent top bar.
 */
const Header: React.FC = () => {
  return (
    <header style={headerStyles.root}>
      <div style={headerStyles.container}>
        <h1 style={headerStyles.title}>
          A Cool New Web Application for Managing Tasks
        </h1>
        {/* Placeholder for future navigation or user actions */}
        {/* <nav>
          <a href="/">Home</a>
          <a href="/tasks">Tasks</a>
        </nav> */}
      </div>
    </header>
  );
};

// Basic inline styles for the Header component.
// In a larger application, consider using CSS Modules, Styled Components, or a utility-first CSS framework like Tailwind CSS.
const headerStyles: { [key: string]: React.CSSProperties } = {
  root: {
    backgroundColor: '#007bff', // A primary blue color, common for headers
    color: '#ffffff',
    padding: '1rem 0',
    boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
  },
  container: {
    maxWidth: '1140px', // Common container width
    margin: '0 auto',
    padding: '0 1rem', // Padding for smaller screens
    display: 'flex',
    justifyContent: 'space-between', // Align title and potential nav items
    alignItems: 'center',
  },
  title: {
    margin: 0,
    fontSize: '1.75rem',
    fontWeight: 500,
  },
  // Example style for navigation if added later
  // navLink: {
  //   color: '#ffffff',
  //   marginLeft: '1rem',
  //   textDecoration: 'none',
  //   fontSize: '1rem',
  // },
};

export default Header;