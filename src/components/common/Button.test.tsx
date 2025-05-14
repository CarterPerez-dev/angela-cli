import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

// Assuming Button.tsx is in the same directory as Button.test.tsx,
// or in a subdirectory that resolves correctly (e.g., src/components/Button/Button.tsx)
import Button from './Button';

// Define a simplified interface for ButtonProps for test clarity.
// The actual ButtonProps would be imported or defined in Button.tsx.
interface TestButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'danger';
  size?: 'small' | 'medium' | 'large';
}

describe('Button Component', () => {
  test('renders correctly with children', () => {
    render(<Button>Click Me</Button>);
    const buttonElement = screen.getByRole('button', { name: /click me/i });
    expect(buttonElement).toBeInTheDocument();
  });

  test('calls onClick handler when clicked', () => {
    const handleClick = jest.fn();
    render(<Button onClick={handleClick}>Submit</Button>);
    const buttonElement = screen.getByRole('button', { name: /submit/i });
    fireEvent.click(buttonElement);
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  test('is disabled when the disabled prop is true', () => {
    render(<Button disabled>Disabled Button</Button>);
    const buttonElement = screen.getByRole('button', { name: /disabled button/i });
    expect(buttonElement).toBeDisabled();
  });

  test('does not call onClick handler when disabled', () => {
    const handleClick = jest.fn();
    render(<Button onClick={handleClick} disabled>Cannot Click</Button>);
    const buttonElement = screen.getByRole('button', { name: /cannot click/i });
    // Attempt to click the disabled button
    fireEvent.click(buttonElement);
    expect(handleClick).not.toHaveBeenCalled();
  });

  test('applies custom className alongside its own classes', () => {
    const customClass = 'my-custom-button';
    render(<Button className={customClass} variant="primary">Styled Button</Button>);
    const buttonElement = screen.getByRole('button', { name: /styled button/i });
    expect(buttonElement).toHaveClass(customClass);
    // Assuming 'btn-primary' is a class added by the variant prop
    expect(buttonElement).toHaveClass('btn-primary');
  });

  test('applies variant class when variant prop is provided', () => {
    // This test assumes the Button component adds a specific class for variants, e.g., 'btn-primary'.
    render(<Button variant="primary">Primary Button</Button> as React.ReactElement<TestButtonProps>);
    const buttonElement = screen.getByRole('button', { name: /primary button/i });
    expect(buttonElement).toHaveClass('btn-primary'); // Adjust class name based on actual implementation
  });

  test('applies size class when size prop is provided', () => {
    // This test assumes the Button component adds a specific class for sizes, e.g., 'btn-large'.
    render(<Button size="large">Large Button</Button> as React.ReactElement<TestButtonProps>);
    const buttonElement = screen.getByRole('button', { name: /large button/i });
    expect(buttonElement).toHaveClass('btn-large'); // Adjust class name based on actual implementation
  });

  test('renders with default type "button" if not specified', () => {
    render(<Button>Default Type</Button>);
    const buttonElement = screen.getByRole('button', { name: /default type/i });
    expect(buttonElement).toHaveAttribute('type', 'button');
  });

  test('renders with specified HTML button type (e.g., "submit")', () => {
    render(<Button type="submit">Submit Type</Button>);
    const buttonElement = screen.getByRole('button', { name: /submit type/i });
    expect(buttonElement).toHaveAttribute('type', 'submit');
  });

  test('passes through other HTML button attributes', () => {
    render(<Button aria-label="Custom Action">Action</Button>);
    const buttonElement = screen.getByRole('button', { name: /custom action/i });
    expect(buttonElement).toBeInTheDocument();
  });

  test('matches snapshot for basic rendering', () => {
    const { asFragment } = render(<Button>Snapshot Me</Button>);
    expect(asFragment()).toMatchSnapshot();
  });

  test('matches snapshot with variant and size props', () => {
    const { asFragment } = render(
      <Button variant="secondary" size="small">
        Snapshot Variant and Size
      </Button> as React.ReactElement<TestButtonProps>
    );
    expect(asFragment()).toMatchSnapshot();
  });
});