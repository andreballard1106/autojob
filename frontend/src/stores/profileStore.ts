import { create } from 'zustand'
import { Profile, ProfileStats, profileApi } from '../services/api'
import { getErrorMessage } from './utils'

interface ProfileState {
  profiles: Profile[]
  selectedProfile: (Profile & { stats?: ProfileStats }) | null
  isLoading: boolean
  error: string | null

  // Actions
  fetchProfiles: () => Promise<void>
  fetchProfile: (id: string) => Promise<void>
  createProfile: (profile: Partial<Profile>) => Promise<Profile>
  updateProfile: (id: string, profile: Partial<Profile>) => Promise<void>
  deleteProfile: (id: string) => Promise<void>
  uploadResume: (id: string, file: File) => Promise<void>
  setSelectedProfile: (profile: Profile | null) => void
  clearError: () => void
}

export const useProfileStore = create<ProfileState>((set) => ({
  profiles: [],
  selectedProfile: null,
  isLoading: false,
  error: null,

  fetchProfiles: async () => {
    set({ isLoading: true, error: null })
    try {
      const { profiles } = await profileApi.list()
      set({ profiles, isLoading: false })
    } catch (error) {
      set({ error: getErrorMessage(error, 'Failed to fetch profiles'), isLoading: false })
    }
  },

  fetchProfile: async (id: string) => {
    set({ isLoading: true, error: null })
    try {
      const profile = await profileApi.get(id)
      set({ selectedProfile: profile, isLoading: false })
    } catch (error) {
      set({ error: getErrorMessage(error, 'Failed to fetch profile'), isLoading: false })
    }
  },

  createProfile: async (profileData: Partial<Profile>) => {
    set({ isLoading: true, error: null })
    try {
      const profile = await profileApi.create(profileData)
      set((state) => ({ profiles: [...state.profiles, profile], isLoading: false }))
      return profile
    } catch (error) {
      set({ error: getErrorMessage(error, 'Failed to create profile'), isLoading: false })
      throw error
    }
  },

  updateProfile: async (id: string, profileData: Partial<Profile>) => {
    set({ isLoading: true, error: null })
    try {
      const updated = await profileApi.update(id, profileData)
      set((state) => ({
        profiles: state.profiles.map((p) => (p.id === id ? updated : p)),
        selectedProfile: state.selectedProfile?.id === id 
          ? { ...state.selectedProfile, ...updated }
          : state.selectedProfile,
        isLoading: false,
      }))
    } catch (error) {
      set({ error: getErrorMessage(error, 'Failed to update profile'), isLoading: false })
      throw error
    }
  },

  deleteProfile: async (id: string) => {
    set({ isLoading: true, error: null })
    try {
      await profileApi.delete(id)
      set((state) => ({
        profiles: state.profiles.filter((p) => p.id !== id),
        selectedProfile: state.selectedProfile?.id === id ? null : state.selectedProfile,
        isLoading: false,
      }))
    } catch (error) {
      set({ error: getErrorMessage(error, 'Failed to delete profile'), isLoading: false })
      throw error
    }
  },

  uploadResume: async (id: string, file: File) => {
    set({ isLoading: true, error: null })
    try {
      const updated = await profileApi.uploadResume(id, file)
      set((state) => ({
        profiles: state.profiles.map((p) => (p.id === id ? updated : p)),
        selectedProfile: state.selectedProfile?.id === id 
          ? { ...state.selectedProfile, ...updated }
          : state.selectedProfile,
        isLoading: false,
      }))
    } catch (error) {
      set({ error: getErrorMessage(error, 'Failed to upload resume'), isLoading: false })
      throw error
    }
  },

  setSelectedProfile: (profile) => {
    set({ selectedProfile: profile })
  },

  clearError: () => {
    set({ error: null })
  },
}))

