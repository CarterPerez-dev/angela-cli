import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css'; // Global styles for the application
import App from './App'; // The main application component
import reportWebVitals from './reportWebVitals'; // For measuring performance

// Find the root DOM element where the React application will be mounted.
// This element is typically defined in `public/index.html`.
const rootElement = document.getElementById('root');

// Ensure the root element exists before attempting to render the application.
if (!rootElement) {
  throw new Error(
    "Failed to find the root element. Ensure an element with id 'root' exists in your HTML."
  );
}

// Create a root for the React application using the new ReactDOM.createRoot API (React 18+).
const root = ReactDOM.createRoot(rootElement);

// Render the main application component into the root.
// React.StrictMode is a tool for highlighting potential problems in an application.
// It activates additional checks and warnings for its descendants during development.
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();