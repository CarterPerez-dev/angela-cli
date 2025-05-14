import React, { createContext, useContext, useState, ReactNode, useCallback } from 'react';

/**
 * Represents a single task item.
 */
export interface Task {
  id: string;
  text: string;
  completed: boolean;
  createdAt: Date;
}

/**
 * Defines the shape of the application context's state and actions.
 */
interface AppContextType {
  tasks: Task[];
  isLoading: boolean;
  error: string | null;
  addTask: (text: string) => Promise<void>;
  toggleTaskCompletion: (id: string) => void;
  deleteTask: (id: string) => Promise<void>;
  updateTaskText: (id: string, newText: string) => void;
  clearError: () => void;
}

// Create the context with an undefined initial value.
// Consumers will use the `useAppContext` hook which provides a non-null assertion.
const AppContext = createContext<AppContextType | undefined>(undefined);

/**
 * Props for the AppProvider component.
 */
interface AppProviderProps {
  children: ReactNode;
}

/**
 * AppProvider component manages the global state for tasks and related operations.
 * It provides the AppContext to its children.
 */
export const AppProvider: React.FC<AppProviderProps> = ({ children }) => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  /**
   * Adds a new task. Simulates an asynchronous API call.
   */
  const addTask = useCallback(async (text: string): Promise<void> => {
    setIsLoading(true);
    setError(null);
    // Simulate API call delay
    await new Promise(resolve => setTimeout(resolve, 500));
    try {
      // In a real app, this would be an API call.
      // For now, we generate a UUID client-side.
      const newTask: Task = {
        id: crypto.randomUUID(),
        text,
        completed: false,
        createdAt: new Date(),
      };
      setTasks(prevTasks => [...prevTasks, newTask]);
    } catch (e) {
      setError("Failed to add task.");
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Toggles the completion status of a task.
   */
  const toggleTaskCompletion = useCallback((id: string) => {
    setTasks(prevTasks =>
      prevTasks.map(task =>
        task.id === id ? { ...task, completed: !task.completed } : task
      )
    );
  }, []);

  /**
   * Deletes a task. Simulates an asynchronous API call.
   */
  const deleteTask = useCallback(async (id: string): Promise<void> => {
    setIsLoading(true);
    setError(null);
    // Simulate API call delay
    await new Promise(resolve => setTimeout(resolve, 300));
    try {
      // In a real app, this would be an API call.
      setTasks(prevTasks => prevTasks.filter(task => task.id !== id));
    } catch (e) {
      setError("Failed to delete task.");
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Updates the text of an existing task.
   */
  const updateTaskText = useCallback((id: string, newText: string) => {
    setTasks(prevTasks =>
      prevTasks.map(task =>
        task.id === id ? { ...task, text: newText } : task
      )
    );
    // Potentially add API call simulation here too if needed
  }, []);

  const contextValue: AppContextType = {
    tasks,
    isLoading,
    error,
    addTask,
    toggleTaskCompletion,
    deleteTask,
    updateTaskText,
    clearError,
  };

  return (
    <AppContext.Provider value={contextValue}>
      {children}
    </AppContext.Provider>
  );
};

/**
 * Custom hook to consume the AppContext.
 * Provides a convenient way to access context values and ensures the hook is used
 * within an AppProvider.
 * @throws Error if used outside of an AppProvider.
 * @returns The AppContext value.
 */
export const useAppContext = (): AppContextType => {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useAppContext must be used within an AppProvider');
  }
  return context;
};