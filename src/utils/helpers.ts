/**
 * @file helpers.ts
 * @description General utility functions for the "a-cool-new-web-application-for" React project.
 * This file contains helper functions that can be used across various parts of the application.
 */

/**
 * Formats a date object, string, or timestamp into a more readable string.
 * @param date - The date to format. Can be a Date object, a string parsable by Date, or a number (timestamp).
 * @param options - Optional Intl.DateTimeFormatOptions to customize the output.
 * @returns A formatted date string, or an empty string if the date is invalid.
 * @example
 * formatDate(new Date()); // "12/25/2023" (depending on locale and default options)
 * formatDate('2023-12-25T10:00:00.000Z', { year: 'numeric', month: 'long', day: 'numeric' }); // "December 25, 2023"
 */
export const formatDate = (
  date: Date | string | number,
  options?: Intl.DateTimeFormatOptions,
): string => {
  try {
    const dateObj = new Date(date);
    if (isNaN(dateObj.getTime())) {
      // console.warn('Invalid date provided to formatDate:', date);
      return '';
    }
    const defaultOptions: Intl.DateTimeFormatOptions = {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      ...options,
    };
    return new Intl.DateTimeFormat(navigator.language, defaultOptions).format(dateObj);
  } catch (error) {
    // console.error('Error formatting date:', error);
    return '';
  }
};

/**
 * Truncates a string to a specified maximum length and appends an ellipsis if truncated.
 * @param text - The string to truncate.
 * @param maxLength - The maximum length of the string before truncation.
 * @returns The truncated string with an ellipsis, or the original string if it's shorter than maxLength.
 * @example
 * truncateText("This is a long piece of text", 10); // "This is a..."
 */
export const truncateText = (text: string, maxLength: number): string => {
  if (typeof text !== 'string' || typeof maxLength !== 'number' || maxLength <= 0) {
    return text || '';
  }
  if (text.length <= maxLength) {
    return text;
  }
  return `${text.substring(0, maxLength)}...`;
};

/**
 * Capitalizes the first letter of a string.
 * @param str - The string to capitalize.
 * @returns The string with its first letter capitalized, or an empty string if input is invalid.
 * @example
 * capitalizeFirstLetter("hello"); // "Hello"
 */
export const capitalizeFirstLetter = (str: string): string => {
  if (!str || typeof str !== 'string') {
    return '';
  }
  return str.charAt(0).toUpperCase() + str.slice(1);
};

/**
 * Generates initials from a name string.
 * @param name - The full name string.
 * @returns A string containing the initials (e.g., "John Doe" -> "JD"). Returns an empty string for invalid input.
 * @example
 * getInitials("John Doe"); // "JD"
 * getInitials("SingleName"); // "S"
 */
export const getInitials = (name: string): string => {
  if (!name || typeof name !== 'string') {
    return '';
  }
  const nameParts = name.trim().split(/\s+/);
  if (nameParts.length === 0 || nameParts[0] === '') {
    return '';
  }
  if (nameParts.length === 1) {
    return nameParts[0].charAt(0).toUpperCase();
  }
  return (
    nameParts[0].charAt(0) + nameParts[nameParts.length - 1].charAt(0)
  ).toUpperCase();
};

/**
 * A simple utility for conditionally joining class names.
 * Inspired by the 'clsx' library.
 * @param args - Class names or objects with class names as keys and booleans as values.
 * @returns A string of combined class names.
 * @example
 * cn('foo', 'bar'); // "foo bar"
 * cn('foo', { bar: true, duck: false }); // "foo bar"
 * cn('foo', null, 'bar', undefined, { baz: true }); // "foo bar baz"
 */
export const cn = (
  ...args: (string | undefined | null | false | Record<string, boolean>)[]
): string => {
  const classes: string[] = [];
  for (const arg of args) {
    if (typeof arg === 'string' && arg) {
      classes.push(arg);
    } else if (typeof arg === 'object' && arg !== null) {
      for (const key in arg) {
        if (Object.prototype.hasOwnProperty.call(arg, key) && arg[key]) {
          classes.push(key);
        }
      }
    }
  }
  return classes.join(' ');
};

/**
 * Validates if a string is a valid email address format.
 * This is a basic regex check and doesn't guarantee deliverability.
 * @param email - The email string to validate.
 * @returns True if the email format is valid, false otherwise.
 * @example
 * isValidEmail("test@example.com"); // true
 * isValidEmail("invalid-email"); // false
 */
export const isValidEmail = (email: string): boolean => {
  if (!email || typeof email !== 'string') {
    return false;
  }
  // Basic regex for email validation
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

/**
 * Creates a promise that resolves after a specified number of milliseconds.
 * Useful for simulating network latency or debouncing/throttling.
 * @param ms - The number of milliseconds to delay.
 * @returns A promise that resolves after the delay.
 * @example
 * async function exampleUsage() {
 *   console.log("Start");
 *   await delay(1000);
 *   console.log("End after 1 second");
 * }
 */
export const delay = (ms: number): Promise<void> => {
  return new Promise(resolve => setTimeout(resolve, ms));
};

/**
 * Generates a simple pseudo-unique ID.
 * Note: This is not cryptographically secure or guaranteed to be globally unique.
 * For robust unique IDs, consider using a library like `uuid`.
 * @returns A pseudo-unique string ID.
 * @example
 * const id = generateSimpleId(); // e.g., "l7k8c2mxaq8o1pqrst"
 */
export const generateSimpleId = (): string => {
  return Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
};

/**
 * Safely parses a JSON string.
 * @param jsonString - The JSON string to parse.
 * @param defaultValue - The value to return if parsing fails.
 * @returns The parsed object or the default value.
 * @template T - The expected type of the parsed object.
 */
export const safeJsonParse = <T>(jsonString: string | null | undefined, defaultValue: T): T => {
  if (!jsonString) {
    return defaultValue;
  }
  try {
    return JSON.parse(jsonString) as T;
  } catch (error) {
    // console.warn('Failed to parse JSON string:', error);
    return defaultValue;
  }
};

/**
 * Scrolls to the top of the page smoothly.
 */
export const scrollToTop = (): void => {
  try {
    window.scrollTo({
      top: 0,
      behavior: 'smooth',
    });
  } catch (error) {
    // Fallback for browsers that don't support smooth scrolling options
    window.scrollTo(0, 0);
  }
};

/**
 * Checks if the current environment is development.
 * Relies on NODE_ENV, commonly set by build tools like Create React App.
 * @returns True if in development mode, false otherwise.
 */
export const isDevelopmentEnv = (): boolean => {
  return process.env.NODE_ENV === 'development';
};