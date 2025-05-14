import React from 'react';

/**
 * About Page Component
 *
 * Displays information about the "a-cool-new-web-application-for" project.
 * This component is typically used as a route in a React application (e.g., in `src/pages/About.tsx`).
 */
const About: React.FC = () => {
  const appName = "a-cool-new-web-application-for";

  return (
    <div className="about-page-container"> {/* Assumes CSS classes for styling */}
      <header className="about-header" style={{ textAlign: 'center', marginBottom: '2rem' }}>
        <h1>About {appName}</h1>
      </header>

      <section className="about-content" style={{ maxWidth: '800px', margin: '0 auto', padding: '0 1rem' }}>
        <p>
          Welcome to <strong>{appName}</strong>! This is a cool new web application
          designed to help you manage your tasks effectively.
        </p>
        <p>
          Our goal is to provide a seamless and intuitive experience for organizing
          your daily to-dos, tracking progress, and boosting your productivity.
          This application is built with React.
        </p>

        <div className="about-section" style={{ marginTop: '2rem' }}>
          <h2 style={{ borderBottom: '1px solid #eee', paddingBottom: '0.5rem', marginBottom: '1rem' }}>
            Technology Stack
          </h2>
          <p>
            This application is proudly built using modern web technologies:
          </p>
          <ul>
            <li><strong>React:</strong> A JavaScript library for building user interfaces.</li>
            <li><strong>TypeScript:</strong> For strong typing, better tooling, and improved developer experience.</li>
            {/* Future technologies can be listed here, e.g., state management libraries, UI component kits */}
          </ul>
        </div>

        <div className="about-section" style={{ marginTop: '2rem' }}>
          <h2 style={{ borderBottom: '1px solid #eee', paddingBottom: '0.5rem', marginBottom: '1rem' }}>
            Our Mission
          </h2>
          <p>
            To simplify task management and empower users to achieve their goals
            with an easy-to-use and powerful tool. We aim to create a cool new web application
            that makes managing tasks a breeze.
          </p>
        </div>

        {/*
          Future sections could include:
          - Key Features
          - Meet the Team
          - Contact Information
          - Version History / Changelog
        */}
      </section>

      <footer className="about-footer" style={{ textAlign: 'center', marginTop: '3rem', paddingTop: '1rem', borderTop: '1px solid #eee', fontSize: '0.9em', color: '#666' }}>
        <p>&copy; {new Date().getFullYear()} {appName}. All rights reserved.</p>
        <p>Current Version: 0.1.0 (Development)</p>
      </footer>
    </div>
  );
};

export default About;