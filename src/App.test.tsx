import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './App'; // Assumes App.tsx is in the same directory (e.g., src/)

test('renders application with content related to tasks or its name', () => {
  render(<App />);
  
  // This test checks for the presence of text that indicates the application's purpose
  // (e.g., "task management") or its name ("a-cool-new-web-application-for").
  // This is a common initial test to ensure the App component renders some expected high-level content.
  // You may need to adjust the regular expression based on the actual text rendered by your App component.
  const expectedTextPattern = /task(s)?|management|a-cool-new-web-application-for/i;
  
  // screen.getByText will throw an error if the text is not found,
  // which will cause the test to fail as expected.
  const appContentElement = screen.getByText(expectedTextPattern);
  expect(appContentElement).toBeInTheDocument();
});

// Example of another simple test: ensuring the component renders without crashing.
// Note: The test above already covers this implicitly if it passes,
// as rendering is the first step. However, an explicit test can sometimes be useful.
test('renders App component without crashing', () => {
  const { container } = render(<App />);
  // This assertion checks that the component renders *something* into the DOM.
  expect(container.firstChild).toBeInTheDocument();
});