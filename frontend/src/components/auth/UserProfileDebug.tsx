/**
 * Debug version of UserProfile component
 */
import React from 'react';
import { useAuth } from '../../hooks/useAuth';

export const UserProfileDebug: React.FC = () => {
  const { user, isAuthenticated, isLoading, error } = useAuth();

  console.log('UserProfileDebug render:', {
    user,
    isAuthenticated,
    isLoading,
    error,
    hasUser: !!user,
    userKeys: user ? Object.keys(user) : null
  });

  return (
    <div className="max-w-2xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-4">Profile Debug</h1>
      
      <div className="bg-gray-100 p-4 rounded mb-4">
        <h2 className="font-bold mb-2">Auth State:</h2>
        <p><strong>isAuthenticated:</strong> {String(isAuthenticated)}</p>
        <p><strong>isLoading:</strong> {String(isLoading)}</p>
        <p><strong>hasUser:</strong> {String(!!user)}</p>
        <p><strong>error:</strong> {error || 'null'}</p>
      </div>

      {user && (
        <div className="bg-green-100 p-4 rounded mb-4">
          <h2 className="font-bold mb-2">User Data:</h2>
          <pre className="text-sm">{JSON.stringify(user, null, 2)}</pre>
        </div>
      )}

      {isLoading && (
        <div className="bg-yellow-100 p-4 rounded mb-4">
          <p>Loading...</p>
        </div>
      )}

      {error && (
        <div className="bg-red-100 p-4 rounded mb-4">
          <p><strong>Error:</strong> {error}</p>
        </div>
      )}

      {!user && !isLoading && !error && (
        <div className="bg-gray-100 p-4 rounded mb-4">
          <p>No user data available</p>
        </div>
      )}
    </div>
  );
};