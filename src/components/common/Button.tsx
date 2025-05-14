import React from 'react';

/**
 * Props for the Button component.
 * Extends standard HTML button attributes.
 */
export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /**
   * The content to be displayed inside the button.
   * Can be a string, number, or any valid React node (e.g., an icon).
   * Optional, allowing for icon-only buttons.
   */
  children?: React.ReactNode;
  /**
   * The visual style of the button.
   * @default 'primary'
   */
  variant?: 'primary' | 'secondary' | 'danger' | 'outline' | 'ghost' | 'link';
  /**
   * The size of the button.
   * @default 'md'
   */
  size?: 'sm' | 'md' | 'lg';
  /**
   * If `true`, the button will be disabled.
   * This will be overridden by `isLoading` if `isLoading` is true.
   * @default false
   */
  disabled?: boolean;
  /**
   * If `true`, the button will display a loading indicator and be disabled.
   * The loading indicator replaces `leftIcon` if present, otherwise it's placed before `children`.
   * `children` (if `leftIcon` was not present) and `rightIcon` are hidden when `isLoading` is true.
   * @default false
   */
  isLoading?: boolean;
  /**
   * Optional icon to display before the button text. Replaced by a spinner when `isLoading` is true.
   * Icons should ideally be SVGs that can inherit color (`currentColor`) and size (`1em`).
   */
  leftIcon?: React.ReactElement;
  /**
   * Optional icon to display after the button text. Hidden when `isLoading` is true.
   * Icons should ideally be SVGs that can inherit color (`currentColor`) and size (`1em`).
   */
  rightIcon?: React.ReactElement;
  /**
   * Optional additional CSS classes to apply to the button.
   */
  className?: string;
  /**
   * The HTML button type.
   * @default 'button'
   */
  type?: 'button' | 'submit' | 'reset';
  /**
   * If `true`, the button will take the full width of its container.
   * @default false
   */
  fullWidth?: boolean;
}

// A basic SVG spinner component. In a real application, this might be more sophisticated
// or come from an icon library.
const DefaultSpinner: React.FC<{ className?: string; sizeClass?: string }> = ({
  className,
  sizeClass = 'h-5 w-5', // Default size
}) => (
  <svg
    className={`animate-spin text-current ${sizeClass} ${className || ''}`}
    xmlns="http://www.w3.org/2000/svg"
    fill="none"
    viewBox="0 0 24 24"
    aria-hidden="true" // Hide from screen readers as its state is conveyed by `isLoading` and `disabled`
  >
    <circle
      className="opacity-25"
      cx="12"
      cy="12"
      r="10"
      stroke="currentColor"
      strokeWidth="4"
    ></circle>
    <path
      className="opacity-75"
      fill="currentColor"
      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
    ></path>
  </svg>
);

/**
 * A reusable Button component for the "a-cool-new-web-application-for" project.
 *
 * This component provides a flexible and stylable button, supporting different
 * visual variants, sizes, loading states, icons, and full-width display.
 * It's designed to be easily integrated and customized within the application.
 *
 * Styling is intended to be handled via CSS classes, potentially with a
 * framework like Tailwind CSS. The provided classes are examples.
 * For icon sizing, ensure icons adapt to text size (e.g., using `em` units or `currentColor` if SVG).
 */
const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  disabled = false,
  isLoading = false,
  leftIcon,
  rightIcon,
  className = '',
  type = 'button',
  fullWidth = false,
  ...props
}) => {
  // Base classes for all buttons
  const baseClasses =
    'inline-flex items-center justify-center font-semibold focus:outline-none focus:ring-2 focus:ring-offset-2 dark:focus:ring-offset-gray-800 focus:ring-opacity-75 rounded-md shadow-sm transition-all duration-150 ease-in-out';

  // Classes for different variants (example using Tailwind CSS conventions)
  const variantClasses: Record<NonNullable<ButtonProps['variant']>, string> = {
    primary: 'bg-indigo-600 hover:bg-indigo-700 text-white focus:ring-indigo-500',
    secondary:
      'bg-gray-200 hover:bg-gray-300 text-gray-800 focus:ring-indigo-500 dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-gray-100',
    danger: 'bg-red-600 hover:bg-red-700 text-white focus:ring-red-500',
    outline:
      'bg-transparent border border-indigo-600 text-indigo-600 hover:bg-indigo-50 focus:ring-indigo-500 dark:text-indigo-400 dark:border-indigo-500 dark:hover:bg-indigo-900/30',
    ghost:
      'bg-transparent hover:bg-gray-100 text-gray-700 focus:ring-indigo-500 dark:text-gray-300 dark:hover:bg-gray-700/60',
    link: 'bg-transparent text-indigo-600 hover:text-indigo-800 hover:underline p-0 focus:ring-indigo-500 dark:text-indigo-400 dark:hover:text-indigo-300',
  };

  // Classes for different sizes (text size and padding)
  const textSizeClasses: Record<NonNullable<ButtonProps['size']>, string> = {
    sm: 'text-sm',
    md: 'text-base',
    lg: 'text-lg',
  };
  const paddingClasses: Record<NonNullable<ButtonProps['size']>, string> = {
    sm: 'py-1.5 px-3',
    md: 'py-2 px-4',
    lg: 'py-2.5 px-6',
  };
  const spinnerSizeClasses: Record<NonNullable<ButtonProps['size']>, string> = {
    sm: 'h-4 w-4',
    md: 'h-5 w-5',
    lg: 'h-6 w-6',
  };

  const actualDisabled = isLoading || disabled;
  const disabledClasses = actualDisabled ? 'opacity-60 cursor-not-allowed' : '';
  const fullWidthClasses = fullWidth ? 'w-full' : '';

  // Link variant typically has no padding unless it's an icon-only button where padding might be desired.
  // For simplicity, 'link' variant has p-0. If specific padding for icon-only links is needed,
  // it can be added via `className` or by refining this logic.
  const currentPadding = variant === 'link' ? 'p-0' : paddingClasses[size];

  const combinedClassName = [
    baseClasses,
    variantClasses[variant],
    textSizeClasses[size],
    currentPadding,
    disabledClasses,
    fullWidthClasses,
    className, // User-provided classes should come last to allow overrides
  ]
    .filter(Boolean) // Remove any empty strings from conditional classes
    .join(' ');

  // Icon margin utility: adds margin if there's text (children) next to the icon.
  const getIconSpacingClass = (hasText: boolean, position: 'left' | 'right'): string => {
    if (!hasText) return '';
    const marginValue = { sm: '1.5', md: '2', lg: '2' }[size]; // Tailwind spacing units
    return position === 'left' ? `mr-${marginValue}` : `ml-${marginValue}`;
  };

  const spinnerElement = (
    <DefaultSpinner
      sizeClass={spinnerSizeClasses[size]}
      className={getIconSpacingClass(!!children && !leftIcon, 'left')} // Add margin if spinner is next to text
    />
  );

  const renderLeftIcon = () => {
    if (isLoading) return spinnerElement;
    if (leftIcon) {
      return React.cloneElement(leftIcon, {
        'aria-hidden': true,
        className: `${leftIcon.props.className || ''} ${getIconSpacingClass(!!children, 'left')}`.trim(),
      });
    }
    return null;
  };

  const renderRightIcon = () => {
    // Don't show right icon if loading (spinner takes precedence or is on left)
    if (isLoading || !rightIcon) return null;
    return React.cloneElement(rightIcon, {
      'aria-hidden': true,
      className: `${rightIcon.props.className || ''} ${getIconSpacingClass(!!children, 'right')}`.trim(),
    });
  };

  // Determine what content to display inside the button
  let buttonInnerContent = children;
  if (isLoading) {
    // If loading and there was no original leftIcon, the spinner takes the place of children.
    // If there was a leftIcon, it's replaced by the spinner, and children are still shown.
    if (!leftIcon) {
      buttonInnerContent = null; // Spinner is shown as the primary content via renderLeftIcon
    }
  }

  return (
    <button
      type={type}
      className={combinedClassName}
      disabled={actualDisabled}
      {...props} // Spread remaining props like onClick, aria-attributes, etc.
    >
      {renderLeftIcon()}
      {buttonInnerContent}
      {renderRightIcon()}
    </button>
  );
};

export default Button;
