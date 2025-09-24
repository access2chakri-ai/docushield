"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { isAuthenticated, getUserData, authenticatedFetch, type User } from '@/utils/auth';
import { config } from '@/utils/config';

interface ProfilePhotoResponse {
  success: boolean;
  image_url: string;
  prompt: string;
  model: string;
  provider: string;
  estimated_cost: number;
}

export default function ProfilePage() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // Profile update states
  const [name, setName] = useState('');
  const [updatingProfile, setUpdatingProfile] = useState(false);
  
  // Password change states
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [changingPassword, setChangingPassword] = useState(false);
  
  // Photo generation states
  const [photoPrompt, setPhotoPrompt] = useState('');
  const [generatingPhoto, setGeneratingPhoto] = useState(false);
  const [photoSize, setPhotoSize] = useState('1024x1024');
  const [photoQuality, setPhotoQuality] = useState('standard');
  const [photoStyle, setPhotoStyle] = useState('vivid');
  
  const router = useRouter();

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push('/auth');
      return;
    }

    const currentUser = getUserData();
    if (currentUser) {
      setUser(currentUser);
      setName(currentUser.name);
      setLoading(false);
    } else {
      fetchUserProfile();
    }
  }, [router]);

  const fetchUserProfile = async () => {
    try {
      const response = await authenticatedFetch(`${config.apiBaseUrl}/api/profile/me`);
      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
        setName(userData.name);
      } else {
        setError('Failed to load profile');
      }
    } catch (err) {
      setError('Failed to connect to server');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setUpdatingProfile(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await authenticatedFetch(`${config.apiBaseUrl}/api/profile/update`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name }),
      });

      if (response.ok) {
        const updatedUser = await response.json();
        setUser(updatedUser);
        setSuccess('Profile updated successfully!');
        
        // Update localStorage
        localStorage.setItem('docushield_user', JSON.stringify(updatedUser));
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Profile update failed');
      }
    } catch (err) {
      setError('Failed to update profile');
    } finally {
      setUpdatingProfile(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setChangingPassword(true);
    setError(null);
    setSuccess(null);

    if (newPassword !== confirmPassword) {
      setError('New passwords do not match');
      setChangingPassword(false);
      return;
    }

    if (newPassword.length < 8) {
      setError('New password must be at least 8 characters long');
      setChangingPassword(false);
      return;
    }

    try {
      const response = await authenticatedFetch(`${config.apiBaseUrl}/api/profile/change-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });

      if (response.ok) {
        setSuccess('Password changed successfully!');
        setCurrentPassword('');
        setNewPassword('');
        setConfirmPassword('');
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Password change failed');
      }
    } catch (err) {
      setError('Failed to change password');
    } finally {
      setChangingPassword(false);
    }
  };

  const handleGeneratePhoto = async (e: React.FormEvent) => {
    e.preventDefault();
    setGeneratingPhoto(true);
    setError(null);
    setSuccess(null);

    if (!photoPrompt.trim()) {
      setError('Please enter a prompt for your profile photo');
      setGeneratingPhoto(false);
      return;
    }

    try {
      const response = await authenticatedFetch(`${config.apiBaseUrl}/api/profile/generate-photo`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          prompt: photoPrompt,
          size: photoSize,
          quality: photoQuality,
          style: photoStyle,
        }),
      }, 60000); // 60 second timeout for image generation

      if (response.ok) {
        const photoData: ProfilePhotoResponse = await response.json();
        
        // Update user state with new photo
        const updatedUser = { ...user!, profile_photo_url: photoData.image_url, profile_photo_prompt: photoPrompt };
        setUser(updatedUser);
        
        // Update localStorage
        localStorage.setItem('docushield_user', JSON.stringify(updatedUser));
        
        setSuccess(`Profile photo generated successfully! (Cost: $${photoData.estimated_cost.toFixed(3)})`);
        setPhotoPrompt('');
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Photo generation failed');
      }
    } catch (err) {
      if (err instanceof Error && err.message.includes('timed out')) {
        setError('Photo generation timed out. Please try again with a simpler prompt.');
      } else {
        setError('Failed to generate profile photo');
      }
    } finally {
      setGeneratingPhoto(false);
    }
  };

  const handleRemovePhoto = async () => {
    setError(null);
    setSuccess(null);

    try {
      const response = await authenticatedFetch(`${config.apiBaseUrl}/api/profile/photo`, {
        method: 'DELETE',
      });

      if (response.ok) {
        const updatedUser = { ...user!, profile_photo_url: null, profile_photo_prompt: null };
        setUser(updatedUser);
        
        // Update localStorage
        localStorage.setItem('docushield_user', JSON.stringify(updatedUser));
        
        setSuccess('Profile photo removed successfully!');
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Photo removal failed');
      }
    } catch (err) {
      setError('Failed to remove profile photo');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Profile Settings</h1>
            <p className="text-gray-600">Manage your account settings and preferences</p>
          </div>

          {/* Error/Success Messages */}
          {error && (
            <div className="mb-6 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-lg">
              {error}
            </div>
          )}
          {success && (
            <div className="mb-6 bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded-lg">
              {success}
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Profile Photo Section */}
            <div className="lg:col-span-1">
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">Profile Photo</h2>
                
                <div className="text-center mb-6">
                  {user?.profile_photo_url ? (
                    <div className="relative inline-block">
                      <img
                        src={user.profile_photo_url}
                        alt="Profile"
                        className="w-32 h-32 rounded-full object-cover border-4 border-indigo-100"
                      />
                      <button
                        onClick={handleRemovePhoto}
                        className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full w-8 h-8 flex items-center justify-center hover:bg-red-600 transition-colors"
                        title="Remove photo"
                      >
                        ×
                      </button>
                    </div>
                  ) : (
                    <div className="w-32 h-32 rounded-full bg-gradient-to-br from-indigo-400 to-purple-500 flex items-center justify-center text-white text-4xl font-bold mx-auto">
                      {user?.name?.charAt(0)?.toUpperCase() || 'U'}
                    </div>
                  )}
                  
                  {user?.profile_photo_prompt && (
                    <p className="text-sm text-gray-500 mt-2">
                      Generated from: "{user.profile_photo_prompt}"
                    </p>
                  )}
                </div>

                {/* Generate Photo Form */}
                <form onSubmit={handleGeneratePhoto} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Photo Prompt
                    </label>
                    <input
                      type="text"
                      value={photoPrompt}
                      onChange={(e) => setPhotoPrompt(e.target.value)}
                      placeholder="e.g., professional business person, smiling, casual attire"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Size
                      </label>
                      <select
                        value={photoSize}
                        onChange={(e) => setPhotoSize(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
                      >
                        <option value="1024x1024">1024x1024</option>
                        <option value="512x512">512x512</option>
                        <option value="256x256">256x256</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Quality
                      </label>
                      <select
                        value={photoQuality}
                        onChange={(e) => setPhotoQuality(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
                      >
                        <option value="standard">Standard</option>
                        <option value="hd">HD</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Style
                    </label>
                    <select
                      value={photoStyle}
                      onChange={(e) => setPhotoStyle(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
                    >
                      <option value="vivid">Vivid</option>
                      <option value="natural">Natural</option>
                    </select>
                  </div>

                  <button
                    type="submit"
                    disabled={generatingPhoto}
                    className="w-full bg-indigo-600 text-white py-2 px-4 rounded-md hover:bg-indigo-700 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {generatingPhoto ? (
                      <div className="flex items-center justify-center">
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                        Generating...
                      </div>
                    ) : (
                      'Generate AI Photo'
                    )}
                  </button>
                </form>
              </div>
            </div>

            {/* Profile Info & Password Section */}
            <div className="lg:col-span-2 space-y-8">
              {/* Profile Information */}
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">Profile Information</h2>
                
                <form onSubmit={handleUpdateProfile} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Full Name
                    </label>
                    <input
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Email Address
                    </label>
                    <input
                      type="email"
                      value={user?.email || ''}
                      disabled
                      className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50 text-gray-500"
                    />
                    <p className="text-sm text-gray-500 mt-1">Email cannot be changed</p>
                  </div>

                  <button
                    type="submit"
                    disabled={updatingProfile}
                    className="bg-indigo-600 text-white py-2 px-6 rounded-md hover:bg-indigo-700 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {updatingProfile ? 'Updating...' : 'Update Profile'}
                  </button>
                </form>
              </div>

              {/* Change Password */}
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">Change Password</h2>
                
                <form onSubmit={handleChangePassword} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Current Password
                    </label>
                    <input
                      type="password"
                      value={currentPassword}
                      onChange={(e) => setCurrentPassword(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      New Password
                    </label>
                    <input
                      type="password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
                      required
                      minLength={8}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Confirm New Password
                    </label>
                    <input
                      type="password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
                      required
                      minLength={8}
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={changingPassword}
                    className="bg-red-600 text-white py-2 px-6 rounded-md hover:bg-red-700 focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {changingPassword ? 'Changing...' : 'Change Password'}
                  </button>
                </form>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
