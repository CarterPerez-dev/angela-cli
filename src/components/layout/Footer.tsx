import React from 'react';

/**
 * Footer component for the application.
 * Displays copyright information and the current year.
 */
const Footer: React.FC = () => {
  const currentYear = new Date().getFullYear();

  return (
    <footer style={footerStyle}>
      <p style={textStyle}>
        &copy; {currentYear} A Cool New Web Application For. All rights reserved.
      </p>
    </footer>
  );
};

// Basic inline styles for the footer
const footerStyle: React.CSSProperties = {
  backgroundColor: '#f8f9fa', // A light grey background
  padding: '20px',
  textAlign: 'center',
  borderTop: '1px solid #e7e7e7', // A subtle top border
  position: 'fixed', // Or 'relative' or 'absolute' depending on layout needs
  left: 0,
  bottom: 0,
  width: '100%',
};

const textStyle: React.CSSProperties = {
  margin: 0,
  fontSize: '0.9rem',
  color: '#6c757d', // A muted text color
};

export default Footer;