import { useState, useEffect, useCallback } from 'react'
import { 
  Plus, 
  Search, 
  Mail,
  Phone,
  FileText,
  Trash2,
  Edit,
  X,
  Loader2,
  Upload,
  ChevronDown,
  ChevronUp,
  Building,
  GraduationCap,
  User,
  Briefcase,
  MapPin,
  Globe,
  Linkedin,
  Github,
  Languages,
  Plane,
  Home,
  Brain,
  Sparkles,
  DollarSign,
  Target
} from 'lucide-react'
import clsx from 'clsx'
import toast from 'react-hot-toast'
import { useDropzone } from 'react-dropzone'
import { useProfileStore } from '../stores/profileStore'
import { Profile, WorkExperience, Education, DocumentContent, profileApi } from '../services/api'

// Empty work experience template
const emptyWorkExperience: WorkExperience = {
  company_name: '',
  job_title: '',
  work_style: 'onsite',
  start_date: '',
  end_date: '',
  address_1: '',
  address_2: '',
  city: '',
  state: '',
  country: '',
  zip_code: '',
  document_paths: [],
}

// Empty education template
const emptyEducation: Education = {
  university_name: '',
  degree: '',
  major: '',
  location: '',
  start_date: '',
  end_date: '',
}

// Empty profile template
const emptyProfile: Partial<Profile> = {
  first_name: '',
  middle_name: '',
  last_name: '',
  preferred_first_name: '',
  email: '',
  phone: '',
  location: '',
  preferred_password: '',
  // Detailed address for job applications
  address_1: '',
  address_2: '',
  county: '',
  city: '',
  state: '',
  country: '',
  zip_code: '',
  // URLs
  linkedin_url: '',
  github_url: '',
  // Demographics
  gender: '',
  nationality: '',
  veteran_status: '',
  disability_status: '',
  willing_to_travel: false,
  willing_to_relocate: false,
  primary_language: '',
  work_experience: [],
  education: [],
  skills: [],
  // AI Customization
  personal_brand: '',
  key_achievements: [],
  priority_skills: [],
  target_industries: [],
  target_roles: [],
  resume_tone_override: '',
  custom_question_answers: {},
  salary_min: undefined,
  salary_max: undefined,
  salary_currency: 'USD',
}

export default function Profiles() {
  const [searchQuery, setSearchQuery] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [formData, setFormData] = useState<Partial<Profile>>(emptyProfile)
  const [expandedSections, setExpandedSections] = useState({
    userInfo: true,
    workHistory: true,
    education: true,
    aiCustomization: false,
  })
  
  // Document viewer modal state
  const [showDocumentViewer, setShowDocumentViewer] = useState(false)
  const [documentViewerContent, setDocumentViewerContent] = useState<DocumentContent | null>(null)
  const [documentViewerLoading, setDocumentViewerLoading] = useState(false)
  
  // Resume viewer modal state
  const [showResumeViewer, setShowResumeViewer] = useState(false)
  const [resumeViewerUrl, setResumeViewerUrl] = useState<string | null>(null)
  const [resumeViewerFilename, setResumeViewerFilename] = useState<string>('')
  
  // Resume upload state
  const [resumeUploading, setResumeUploading] = useState(false)
  
  // Cover letter template state
  const [coverLetterUploading, setCoverLetterUploading] = useState(false)
  const [showCoverLetterGenerator, setShowCoverLetterGenerator] = useState(false)
  const [coverLetterContent, setCoverLetterContent] = useState('')
  const [coverLetterGenerating, setCoverLetterGenerating] = useState(false)
  const [generatedCoverLetterUrl, setGeneratedCoverLetterUrl] = useState<string | null>(null)
  const [generatedCoverLetterId, setGeneratedCoverLetterId] = useState<string | null>(null)

  const { 
    profiles, 
    selectedProfile,
    isLoading, 
    error, 
    fetchProfiles, 
    fetchProfile,
    createProfile,
    updateProfile,
    deleteProfile,
    setSelectedProfile,
    clearError 
  } = useProfileStore()

  useEffect(() => {
    fetchProfiles()
  }, [fetchProfiles])

  const filteredProfiles = profiles.filter(profile =>
    profile.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    profile.email.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const openCreateModal = () => {
    setFormData(emptyProfile)
    setIsEditing(false)
    setShowModal(true)
  }

  const openEditModal = async (profileId: string) => {
    await fetchProfile(profileId)
    setIsEditing(true)
    setShowModal(true)
  }

  useEffect(() => {
    if (selectedProfile && isEditing) {
      setFormData({
        ...selectedProfile,
        work_experience: selectedProfile.work_experience || [],
        education: selectedProfile.education || [],
        skills: selectedProfile.skills || [],
      })
    }
  }, [selectedProfile, isEditing])

  const handleSubmit = async () => {
    if (!formData.first_name || !formData.last_name || !formData.email) {
      toast.error('First name, last name, and email are required')
      return
    }

    try {
      if (isEditing && selectedProfile?.id) {
        await updateProfile(selectedProfile.id, formData)
        toast.success('Profile updated successfully')
      } else {
        await createProfile(formData)
        toast.success('Profile created successfully')
      }
      setShowModal(false)
      setFormData(emptyProfile)
    } catch {
      toast.error(isEditing ? 'Failed to update profile' : 'Failed to create profile')
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this profile?')) return
    try {
      await deleteProfile(id)
      toast.success('Profile deleted')
    } catch {
      toast.error('Failed to delete profile')
    }
  }

  const handleCloseModal = () => {
    setShowModal(false)
    setFormData(emptyProfile)
    setSelectedProfile(null)
  }

  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }))
  }

  // Work Experience handlers
  const addWorkExperience = () => {
    setFormData(prev => ({
      ...prev,
      work_experience: [...(prev.work_experience || []), { ...emptyWorkExperience }],
    }))
  }

  const updateWorkExperience = (index: number, field: keyof WorkExperience, value: string | string[]) => {
    setFormData(prev => {
      const work = [...(prev.work_experience || [])]
      work[index] = { ...work[index], [field]: value }
      return { ...prev, work_experience: work }
    })
  }

  const removeWorkExperience = (index: number) => {
    setFormData(prev => ({
      ...prev,
      work_experience: (prev.work_experience || []).filter((_, i) => i !== index),
    }))
  }

  // Education handlers
  const addEducation = () => {
    setFormData(prev => ({
      ...prev,
      education: [...(prev.education || []), { ...emptyEducation }],
    }))
  }

  const updateEducation = (index: number, field: keyof Education, value: string) => {
    setFormData(prev => {
      const edu = [...(prev.education || [])]
      edu[index] = { ...edu[index], [field]: value }
      return { ...prev, education: edu }
    })
  }

  const removeEducation = (index: number) => {
    setFormData(prev => ({
      ...prev,
      education: (prev.education || []).filter((_, i) => i !== index),
    }))
  }

  // Cover letter template handlers
  const handleCoverLetterTemplateUpload = useCallback(async (files: File[]) => {
    if (!selectedProfile?.id) {
      toast.error('Please save the profile first')
      return
    }
    if (files.length === 0) return
    
    setCoverLetterUploading(true)
    try {
      await profileApi.uploadCoverLetterTemplate(selectedProfile.id, files[0])
      await fetchProfile(selectedProfile.id)
      toast.success('Cover letter template uploaded')
    } catch {
      toast.error('Failed to upload cover letter template')
    } finally {
      setCoverLetterUploading(false)
    }
  }, [selectedProfile?.id, fetchProfile])

  const handleCoverLetterTemplateDelete = async () => {
    if (!selectedProfile?.id) return
    
    try {
      await profileApi.deleteCoverLetterTemplate(selectedProfile.id)
      await fetchProfile(selectedProfile.id)
      toast.success('Cover letter template deleted')
    } catch {
      toast.error('Failed to delete cover letter template')
    }
  }

  const handleGenerateCoverLetter = async () => {
    if (!selectedProfile?.id || !coverLetterContent.trim()) return
    
    setCoverLetterGenerating(true)
    try {
      const result = await profileApi.generateCoverLetter(selectedProfile.id, coverLetterContent)
      setGeneratedCoverLetterId(result.generation_id)
      setGeneratedCoverLetterUrl(profileApi.getGeneratedCoverLetterUrl(selectedProfile.id, result.generation_id))
    } catch {
      toast.error('Failed to generate cover letter')
    } finally {
      setCoverLetterGenerating(false)
    }
  }

  const closeCoverLetterGenerator = async () => {
    if (generatedCoverLetterId && selectedProfile?.id) {
      try {
        await profileApi.deleteGeneratedCoverLetter(selectedProfile.id, generatedCoverLetterId)
      } catch {
        // Ignore cleanup errors
      }
    }
    setShowCoverLetterGenerator(false)
    setCoverLetterContent('')
    setGeneratedCoverLetterUrl(null)
    setGeneratedCoverLetterId(null)
  }

  // Resume delete handler
  const handleResumeDelete = async () => {
    if (!selectedProfile?.id) return
    
    try {
      await profileApi.deleteResume(selectedProfile.id)
      await fetchProfile(selectedProfile.id)
      toast.success('Resume deleted')
    } catch {
      toast.error('Failed to delete resume')
    }
  }

  // Resume upload handler
  const handleResumeUpload = useCallback(async (files: File[]) => {
    if (!selectedProfile?.id) {
      toast.error('Please save the profile first to upload a resume')
      return
    }
    if (files.length === 0) return
    
    setResumeUploading(true)
    try {
      await profileApi.uploadResume(selectedProfile.id, files[0])
      await fetchProfile(selectedProfile.id)
      toast.success('Resume uploaded successfully')
    } catch {
      toast.error('Failed to upload resume')
    } finally {
      setResumeUploading(false)
    }
  }, [selectedProfile?.id, fetchProfile])

  // View resume file in modal
  const viewResumeFile = () => {
    if (!selectedProfile?.id || !selectedProfile?.resume_path) return
    const url = profileApi.getResumeFileUrl(selectedProfile.id)
    const filename = selectedProfile.resume_path.split(/[/\\]/).pop() || 'Resume'
    setResumeViewerUrl(url)
    setResumeViewerFilename(filename)
    setShowResumeViewer(true)
  }

  // View document content
  const viewDocumentContent = async (workIndex: number, documentPath: string) => {
    if (!selectedProfile?.id) return
    
    setDocumentViewerLoading(true)
    setShowDocumentViewer(true)
    
    try {
      const content = await profileApi.getDocumentContent(selectedProfile.id, workIndex, documentPath)
      setDocumentViewerContent(content)
    } catch {
      toast.error('Failed to load document content')
      setShowDocumentViewer(false)
    } finally {
      setDocumentViewerLoading(false)
    }
  }

  // Document upload component for work experience
  const WorkDocumentUpload = ({ profileId, workIndex, savedWorkCount, onUploadSuccess }: { 
    profileId?: string; 
    workIndex: number;
    savedWorkCount: number;  // Number of work experiences saved in database
    onUploadSuccess: (workExp: WorkExperience) => void;  // Callback to update local state
  }) => {
    // Check if this work experience has been saved to database
    const isWorkExpSaved = profileId && workIndex < savedWorkCount

    const onDrop = useCallback(async (files: File[]) => {
      if (!profileId) {
        toast.error('Please save the profile first to upload documents')
        return
      }
      if (!isWorkExpSaved) {
        toast.error('Please save the profile first. This work experience is not yet saved to the database.')
        return
      }
      try {
        const result = await profileApi.uploadWorkDocuments(profileId, workIndex, files)
        toast.success(`Uploaded ${files.length} document(s)`)
        // Update local formData with new document paths
        onUploadSuccess(result.work_experience)
        // Also refresh profile to sync with server
        fetchProfile(profileId)
      } catch {
        toast.error('Failed to upload documents. Make sure the work experience is saved first.')
      }
    }, [profileId, workIndex, isWorkExpSaved, onUploadSuccess])

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
      onDrop,
      accept: {
        'application/pdf': ['.pdf'],
        'application/msword': ['.doc'],
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
        'text/plain': ['.txt'],
        'text/markdown': ['.md'],
      },
      disabled: !isWorkExpSaved,
    })

    // Show different UI if work experience is not saved yet
    if (!isWorkExpSaved) {
      return (
        <div className="border-2 border-dashed border-amber-500/30 bg-amber-500/5 rounded-lg p-4 text-center">
          <Upload className="w-5 h-5 mx-auto text-amber-500/50" />
          <p className="text-xs text-amber-400 mt-2">
            Save the profile first to enable document uploads
          </p>
          <p className="text-xs text-surface-600">
            Click "Save Changes" below, then you can upload documents
          </p>
        </div>
      )
    }

    return (
      <div 
        {...getRootProps()} 
        className={clsx(
          "border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-colors",
          isDragActive ? "border-primary-500 bg-primary-500/10" : "border-surface-700 hover:border-surface-600"
        )}
      >
        <input {...getInputProps()} />
        <Upload className="w-5 h-5 mx-auto text-surface-500" />
        <p className="text-xs text-surface-400 mt-2">
          {isDragActive ? 'Drop files here' : 'Drop project docs or click to upload'}
        </p>
        <p className="text-xs text-surface-600">PDF, DOC, TXT, MD</p>
      </div>
    )
  }

  const ResumeDropzone = ({ onDrop, isUploading, hasResume }: { 
    onDrop: (files: File[]) => void
    isUploading: boolean
    hasResume: boolean
  }) => {
    const { getRootProps, getInputProps, isDragActive } = useDropzone({
      onDrop,
      accept: {
        'application/pdf': ['.pdf'],
        'application/msword': ['.doc'],
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      },
      multiple: false,
      disabled: isUploading,
    })

    return (
      <div 
        {...getRootProps()} 
        className={clsx(
          "border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-colors",
          isDragActive ? "border-primary-500 bg-primary-500/10" : "border-surface-700 hover:border-surface-600",
          isUploading && "opacity-50 cursor-not-allowed"
        )}
      >
        <input {...getInputProps()} />
        {isUploading ? (
          <>
            <Loader2 className="w-5 h-5 mx-auto text-primary-400 animate-spin" />
            <p className="text-xs text-surface-400 mt-2">Uploading...</p>
          </>
        ) : (
          <>
            <Upload className="w-5 h-5 mx-auto text-surface-500" />
            <p className="text-xs text-surface-400 mt-2">
              {isDragActive ? 'Drop resume here' : hasResume ? 'Drop to replace resume' : 'Drop resume or click to upload'}
            </p>
            <p className="text-xs text-surface-600">PDF, DOC, DOCX</p>
          </>
        )}
      </div>
    )
  }

  const CoverLetterDropzone = ({ onDrop, isUploading, hasTemplate }: { 
    onDrop: (files: File[]) => void
    isUploading: boolean
    hasTemplate: boolean
  }) => {
    const { getRootProps, getInputProps, isDragActive } = useDropzone({
      onDrop,
      accept: {
        'application/msword': ['.doc'],
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      },
      multiple: false,
      disabled: isUploading,
    })

    return (
      <div 
        {...getRootProps()} 
        className={clsx(
          "border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-colors",
          isDragActive ? "border-primary-500 bg-primary-500/10" : "border-surface-700 hover:border-surface-600",
          isUploading && "opacity-50 cursor-not-allowed"
        )}
      >
        <input {...getInputProps()} />
        {isUploading ? (
          <>
            <Loader2 className="w-5 h-5 mx-auto text-primary-400 animate-spin" />
            <p className="text-xs text-surface-400 mt-2">Uploading...</p>
          </>
        ) : (
          <>
            <Upload className="w-5 h-5 mx-auto text-surface-500" />
            <p className="text-xs text-surface-400 mt-2">
              {isDragActive ? 'Drop template here' : hasTemplate ? 'Drop to replace template' : 'Drop template or click to upload'}
            </p>
            <p className="text-xs text-surface-600">DOC, DOCX only</p>
          </>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-display font-bold text-white">Team Profiles</h1>
          <p className="text-surface-400 mt-1">Manage team member profiles for job applications</p>
        </div>
        <button onClick={openCreateModal} className="btn-primary">
          <Plus className="w-4 h-4" />
          Add Profile
        </button>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="card p-4 border-red-500/50 bg-red-500/10 flex justify-between items-center">
          <p className="text-red-400">{error}</p>
          <button onClick={clearError} className="text-red-400 hover:text-red-300">Dismiss</button>
        </div>
      )}

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-surface-500" />
        <input
          type="text"
          placeholder="Search profiles..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="input pl-12"
        />
      </div>

      {/* Profiles Grid */}
      {isLoading && profiles.length === 0 ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-primary-400" />
        </div>
      ) : filteredProfiles.length === 0 ? (
        <div className="card p-12 text-center">
          <User className="w-12 h-12 mx-auto text-surface-600 mb-4" />
          <h3 className="text-lg font-medium text-white">No profiles found</h3>
          <p className="text-surface-400 mt-1">Add a profile to get started</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filteredProfiles.map((profile) => {
            // Build full address string
            const addressParts = [profile.city, profile.state, profile.country].filter(Boolean)
            const fullAddress = addressParts.length > 0 ? addressParts.join(', ') : null
            
            return (
              <div key={profile.id} className="card hover:border-surface-700 transition-all">
                {/* Header with Avatar and Name */}
                <div className="p-5 border-b border-surface-800">
                  <div className="flex items-start gap-4">
                    <div className="w-14 h-14 rounded-full bg-gradient-to-br from-primary-400 to-accent-400 flex items-center justify-center text-xl font-semibold text-white flex-shrink-0">
                      {profile.first_name?.[0]}{profile.last_name?.[0]}
                    </div>
                    <div className="min-w-0 flex-1">
                      <h3 className="font-semibold text-white text-lg truncate">{profile.name}</h3>
                      {profile.location && (
                        <p className="text-sm text-surface-400 truncate">{profile.location}</p>
                      )}
                      {fullAddress && (
                        <div className="flex items-center gap-1.5 mt-1">
                          <MapPin className="w-3 h-3 text-surface-500 flex-shrink-0" />
                          <span className="text-xs text-surface-500 truncate">{fullAddress}</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Contact Info */}
                <div className="p-4 space-y-2 border-b border-surface-800">
                  <div className="flex items-center gap-3 text-sm">
                    <Mail className="w-4 h-4 text-primary-400 flex-shrink-0" />
                    <span className="text-surface-300 truncate">{profile.email}</span>
                  </div>
                  {profile.phone && (
                    <div className="flex items-center gap-3 text-sm">
                      <Phone className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                      <span className="text-surface-300">{profile.phone}</span>
                    </div>
                  )}
                  
                  {/* Social Links */}
                  {(profile.linkedin_url || profile.github_url) && (
                    <div className="flex items-center gap-3 pt-1">
                      {profile.linkedin_url && (
                        <a 
                          href={profile.linkedin_url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300"
                        >
                          <Linkedin className="w-3.5 h-3.5" />
                          LinkedIn
                        </a>
                      )}
                      {profile.github_url && (
                        <a 
                          href={profile.github_url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="flex items-center gap-1.5 text-xs text-surface-400 hover:text-surface-300"
                        >
                          <Github className="w-3.5 h-3.5" />
                          GitHub
                        </a>
                      )}
                    </div>
                  )}
                </div>

                {/* Experience & Education */}
                <div className="p-4 space-y-2 border-b border-surface-800">
                  <div className="flex items-center gap-3 text-sm">
                    <Briefcase className="w-4 h-4 text-amber-400 flex-shrink-0" />
                    <span className="text-surface-300">
                      {(profile.work_experience?.length || 0)} work experience{(profile.work_experience?.length || 0) !== 1 ? 's' : ''}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-sm">
                    <GraduationCap className="w-4 h-4 text-purple-400 flex-shrink-0" />
                    <span className="text-surface-300">
                      {(profile.education?.length || 0)} education{(profile.education?.length || 0) !== 1 ? 's' : ''}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-sm">
                    <FileText className="w-4 h-4 flex-shrink-0" style={{ color: profile.resume_path ? '#34d399' : '#fbbf24' }} />
                    <span className={profile.resume_path ? "text-emerald-400" : "text-amber-400"}>
                      {profile.resume_path ? "Resume uploaded" : "No resume"}
                    </span>
                  </div>
                </div>

                {/* Preferences & Info */}
                <div className="p-4 border-b border-surface-800">
                  <div className="flex flex-wrap gap-2">
                    {profile.primary_language && (
                      <span className="inline-flex items-center gap-1 px-2 py-1 bg-surface-800 rounded text-xs text-surface-300">
                        <Languages className="w-3 h-3" />
                        {profile.primary_language}
                      </span>
                    )}
                    {profile.nationality && (
                      <span className="inline-flex items-center gap-1 px-2 py-1 bg-surface-800 rounded text-xs text-surface-300">
                        <Globe className="w-3 h-3" />
                        {profile.nationality}
                      </span>
                    )}
                    {profile.willing_to_travel && (
                      <span className="inline-flex items-center gap-1 px-2 py-1 bg-blue-500/20 rounded text-xs text-blue-400">
                        <Plane className="w-3 h-3" />
                        Travel OK
                      </span>
                    )}
                    {profile.willing_to_relocate && (
                      <span className="inline-flex items-center gap-1 px-2 py-1 bg-emerald-500/20 rounded text-xs text-emerald-400">
                        <Home className="w-3 h-3" />
                        Relocate OK
                      </span>
                    )}
                  </div>
                </div>

                {/* Actions */}
                <div className="p-4 flex gap-2">
                  <button 
                    onClick={() => openEditModal(profile.id)}
                    className="btn-secondary flex-1 py-2 text-sm"
                  >
                    <Edit className="w-4 h-4" />
                    Edit
                  </button>
                  <button 
                    onClick={() => handleDelete(profile.id)}
                    className="btn-ghost p-2"
                  >
                    <Trash2 className="w-4 h-4 text-red-400" />
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Profile Form Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="card w-full max-w-[1400px] max-h-[90vh] overflow-y-auto animate-slide-up">
            {/* Modal Header */}
            <div className="p-6 border-b border-surface-800 flex items-center justify-between sticky top-0 bg-surface-900 z-10">
              <h2 className="text-xl font-semibold text-white">
                {isEditing ? 'Edit Profile' : 'Create Profile'}
              </h2>
              <button 
                onClick={handleCloseModal}
                className="p-2 rounded-lg hover:bg-surface-800"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-6">
              {/* ================================================ */}
              {/* SECTION 1: USER INFO */}
              {/* ================================================ */}
              <div className="card bg-surface-800/50">
                <button
                  onClick={() => toggleSection('userInfo')}
                  className="w-full p-4 flex items-center justify-between text-left"
                >
                  <div className="flex items-center gap-3">
                    <User className="w-5 h-5 text-primary-400" />
                    <span className="font-medium text-white">User Information</span>
                  </div>
                  {expandedSections.userInfo ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                </button>

                {expandedSections.userInfo && (
                  <div className="p-4 pt-0 space-y-4">
                    {/* Row 1: Names */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                      <div>
                        <label className="label">First Name *</label>
                        <input
                          type="text"
                          value={formData.first_name || ''}
                          onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                          className="input"
                          placeholder="John"
                        />
                      </div>
                      <div>
                        <label className="label">Middle Name</label>
                        <input
                          type="text"
                          value={formData.middle_name || ''}
                          onChange={(e) => setFormData({ ...formData, middle_name: e.target.value })}
                          className="input"
                          placeholder="Michael"
                        />
                      </div>
                      <div>
                        <label className="label">Last Name *</label>
                        <input
                          type="text"
                          value={formData.last_name || ''}
                          onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                          className="input"
                          placeholder="Doe"
                        />
                      </div>
                      <div>
                        <label className="label">Preferred First Name</label>
                        <input
                          type="text"
                          value={formData.preferred_first_name || ''}
                          onChange={(e) => setFormData({ ...formData, preferred_first_name: e.target.value })}
                          className="input"
                          placeholder="Johnny"
                        />
                      </div>
                    </div>

                    {/* Row 2: Contact */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                      <div>
                        <label className="label">Email *</label>
                        <input
                          type="email"
                          value={formData.email || ''}
                          onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                          className="input"
                          placeholder="john@example.com"
                        />
                      </div>
                      <div>
                        <label className="label">Phone</label>
                        <input
                          type="tel"
                          value={formData.phone || ''}
                          onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                          className="input"
                          placeholder="+1 555 123 4567"
                        />
                      </div>
                      <div>
                        <label className="label">Location</label>
                        <input
                          type="text"
                          value={formData.location || ''}
                          onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                          className="input"
                          placeholder="San Francisco, CA"
                        />
                      </div>
                      <div>
                        <label className="label">Preferred Password</label>
                        <input
                          type="password"
                          value={formData.preferred_password || ''}
                          onChange={(e) => setFormData({ ...formData, preferred_password: e.target.value })}
                          className="input"
                          placeholder="For account creation"
                        />
                      </div>
                    </div>

                    {/* Row 3: Detailed Address for Job Applications - All in one line */}
                    <div className="space-y-2">
                      <p className="text-xs text-surface-500">Detailed address for job application forms:</p>
                      <div className="flex gap-3">
                        <div className="flex-[2]">
                          <label className="label">Address Line 1</label>
                          <input
                            type="text"
                            value={formData.address_1 || ''}
                            onChange={(e) => setFormData({ ...formData, address_1: e.target.value })}
                            className="input"
                            placeholder="123 Main Street"
                          />
                        </div>
                        <div className="flex-1">
                          <label className="label">Address Line 2</label>
                          <input
                            type="text"
                            value={formData.address_2 || ''}
                            onChange={(e) => setFormData({ ...formData, address_2: e.target.value })}
                            className="input"
                            placeholder="Apt 4B"
                          />
                        </div>
                        <div className="flex-1">
                          <label className="label">County</label>
                          <input
                            type="text"
                            value={formData.county || ''}
                            onChange={(e) => setFormData({ ...formData, county: e.target.value })}
                            className="input"
                            placeholder="Harris"
                          />
                        </div>
                        <div className="flex-1">
                          <label className="label">City</label>
                          <input
                            type="text"
                            value={formData.city || ''}
                            onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                            className="input"
                            placeholder="Houston"
                          />
                        </div>
                        <div className="w-20">
                          <label className="label">State</label>
                          <input
                            type="text"
                            value={formData.state || ''}
                            onChange={(e) => setFormData({ ...formData, state: e.target.value })}
                            className="input"
                            placeholder="TX"
                          />
                        </div>
                        <div className="flex-1">
                          <label className="label">Country</label>
                          <input
                            type="text"
                            value={formData.country || ''}
                            onChange={(e) => setFormData({ ...formData, country: e.target.value })}
                            className="input"
                            placeholder="United States"
                          />
                        </div>
                        <div className="w-24">
                          <label className="label">Zip Code</label>
                          <input
                            type="text"
                            value={formData.zip_code || ''}
                            onChange={(e) => setFormData({ ...formData, zip_code: e.target.value })}
                            className="input"
                            placeholder="77583"
                          />
                        </div>
                      </div>
                    </div>

                    {/* Row 4: URLs */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div>
                        <label className="label">LinkedIn URL</label>
                        <input
                          type="url"
                          value={formData.linkedin_url || ''}
                          onChange={(e) => setFormData({ ...formData, linkedin_url: e.target.value })}
                          className="input"
                          placeholder="https://linkedin.com/in/johndoe"
                        />
                      </div>
                      <div>
                        <label className="label">GitHub URL</label>
                        <input
                          type="url"
                          value={formData.github_url || ''}
                          onChange={(e) => setFormData({ ...formData, github_url: e.target.value })}
                          className="input"
                          placeholder="https://github.com/johndoe"
                        />
                      </div>
                    </div>

                    {/* Row 4: Demographics */}
                    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
                      <div>
                        <label className="label">Gender</label>
                        <select
                          value={formData.gender || ''}
                          onChange={(e) => setFormData({ ...formData, gender: e.target.value })}
                          className="input"
                        >
                          <option value="">Select...</option>
                          <option value="male">Male</option>
                          <option value="female">Female</option>
                          <option value="non-binary">Non-binary</option>
                          <option value="prefer_not_to_say">Prefer not to say</option>
                        </select>
                      </div>
                      <div>
                        <label className="label">Nationality</label>
                        <input
                          type="text"
                          value={formData.nationality || ''}
                          onChange={(e) => setFormData({ ...formData, nationality: e.target.value })}
                          className="input"
                          placeholder="US Citizen"
                        />
                      </div>
                      <div>
                        <label className="label">Veteran Status</label>
                        <select
                          value={formData.veteran_status || ''}
                          onChange={(e) => setFormData({ ...formData, veteran_status: e.target.value })}
                          className="input"
                        >
                          <option value="">Select...</option>
                          <option value="yes">Yes</option>
                          <option value="no">No</option>
                          <option value="prefer_not_to_say">Prefer not to say</option>
                        </select>
                      </div>
                      <div>
                        <label className="label">Disability</label>
                        <select
                          value={formData.disability_status || ''}
                          onChange={(e) => setFormData({ ...formData, disability_status: e.target.value })}
                          className="input"
                        >
                          <option value="">Select...</option>
                          <option value="yes">Yes</option>
                          <option value="no">No</option>
                          <option value="prefer_not_to_say">Prefer not to say</option>
                        </select>
                      </div>
                      <div>
                        <label className="label">Primary Language</label>
                        <input
                          type="text"
                          value={formData.primary_language || ''}
                          onChange={(e) => setFormData({ ...formData, primary_language: e.target.value })}
                          className="input"
                          placeholder="English"
                        />
                      </div>
                      <div className="flex flex-col justify-end">
                        <label className="flex items-center gap-2 cursor-pointer py-2">
                          <input
                            type="checkbox"
                            checked={formData.willing_to_travel || false}
                            onChange={(e) => setFormData({ ...formData, willing_to_travel: e.target.checked })}
                            className="w-4 h-4 rounded"
                          />
                          <span className="text-sm text-surface-300">Travel OK</span>
                        </label>
                        <label className="flex items-center gap-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={formData.willing_to_relocate || false}
                            onChange={(e) => setFormData({ ...formData, willing_to_relocate: e.target.checked })}
                            className="w-4 h-4 rounded"
                          />
                          <span className="text-sm text-surface-300">Relocate OK</span>
                        </label>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* ================================================ */}
              {/* RESUME UPLOAD SECTION */}
              {/* ================================================ */}
              <div className="card bg-surface-800/50 p-4">
                <div className="flex items-center gap-3 mb-4">
                  <FileText className="w-5 h-5 text-emerald-400" />
                  <span className="font-medium text-white">Resume</span>
                </div>
                
                {isEditing && selectedProfile?.resume_path ? (
                  <div className="space-y-3">
                    <div className="flex items-center gap-3 p-3 bg-surface-900 rounded-lg border border-surface-700 group">
                      <FileText className="w-5 h-5 text-emerald-400" />
                      <button
                        onClick={viewResumeFile}
                        className="text-sm text-surface-300 hover:text-primary-400 transition-colors flex-1 text-left"
                      >
                        {selectedProfile.resume_path.split(/[/\\]/).pop()}
                      </button>
                      <span className="text-xs text-emerald-400">Uploaded</span>
                      <button
                        onClick={handleResumeDelete}
                        className="p-1 rounded hover:bg-red-500/20 text-surface-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all"
                        title="Delete resume"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                    <ResumeDropzone 
                      onDrop={handleResumeUpload} 
                      isUploading={resumeUploading}
                      hasResume={true}
                    />
                  </div>
                ) : isEditing ? (
                  <ResumeDropzone 
                    onDrop={handleResumeUpload} 
                    isUploading={resumeUploading}
                    hasResume={false}
                  />
                ) : (
                  <div className="border-2 border-dashed border-amber-500/30 bg-amber-500/5 rounded-lg p-4 text-center">
                    <Upload className="w-5 h-5 mx-auto text-amber-500/50" />
                    <p className="text-xs text-amber-400 mt-2">
                      Save the profile first to upload a resume
                    </p>
                  </div>
                )}
              </div>

              {/* ================================================ */}
              {/* COVER LETTER TEMPLATE SECTION */}
              {/* ================================================ */}
              <div className="card bg-surface-800/50 p-4">
                <div className="flex items-center gap-3 mb-4">
                  <FileText className="w-5 h-5 text-purple-400" />
                  <span className="font-medium text-white">Cover Letter Template</span>
                </div>
                
                {isEditing && selectedProfile?.cover_letter_template_path ? (
                  <div className="space-y-3">
                    <div className="flex items-center gap-3 p-3 bg-surface-900 rounded-lg border border-surface-700 group">
                      <FileText className="w-5 h-5 text-purple-400" />
                      <span className="text-sm text-surface-300 flex-1">
                        {selectedProfile.cover_letter_template_path.split(/[/\\]/).pop()}
                      </span>
                      <button
                        onClick={() => setShowCoverLetterGenerator(true)}
                        className="px-3 py-1 text-xs bg-purple-500/20 text-purple-400 rounded hover:bg-purple-500/30 transition-colors"
                      >
                        Test Generation
                      </button>
                      <button
                        onClick={handleCoverLetterTemplateDelete}
                        className="p-1 rounded hover:bg-red-500/20 text-surface-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all"
                        title="Delete template"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                    <CoverLetterDropzone 
                      onDrop={handleCoverLetterTemplateUpload} 
                      isUploading={coverLetterUploading}
                      hasTemplate={true}
                    />
                  </div>
                ) : isEditing ? (
                  <CoverLetterDropzone 
                    onDrop={handleCoverLetterTemplateUpload} 
                    isUploading={coverLetterUploading}
                    hasTemplate={false}
                  />
                ) : (
                  <div className="border-2 border-dashed border-amber-500/30 bg-amber-500/5 rounded-lg p-4 text-center">
                    <Upload className="w-5 h-5 mx-auto text-amber-500/50" />
                    <p className="text-xs text-amber-400 mt-2">
                      Save the profile first to upload a template
                    </p>
                  </div>
                )}
              </div>

              {/* ================================================ */}
              {/* SECTION 2: WORK HISTORY */}
              {/* ================================================ */}
              <div className="card bg-surface-800/50">
                <button
                  onClick={() => toggleSection('workHistory')}
                  className="w-full p-4 flex items-center justify-between text-left"
                >
                  <div className="flex items-center gap-3">
                    <Building className="w-5 h-5 text-amber-400" />
                    <span className="font-medium text-white">Work History</span>
                    <span className="text-xs text-surface-500">
                      ({(formData.work_experience || []).length} entries)
                    </span>
                  </div>
                  {expandedSections.workHistory ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                </button>

                {expandedSections.workHistory && (
                  <div className="p-4 pt-0 space-y-4">
                    {(formData.work_experience || []).map((work, index) => (
                      <div key={index} className="p-4 bg-surface-900 rounded-lg space-y-4">
                        <div className="flex items-center justify-between">
                          <h4 className="text-sm font-medium text-white">
                            Experience #{index + 1}
                          </h4>
                          <button
                            onClick={() => removeWorkExperience(index)}
                            className="p-1 text-red-400 hover:text-red-300"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>

                        {/* Row 1: Company, Title, Style, Period */}
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                          <div>
                            <label className="label text-xs">Company Name</label>
                            <input
                              type="text"
                              value={work.company_name}
                              onChange={(e) => updateWorkExperience(index, 'company_name', e.target.value)}
                              className="input text-sm"
                              placeholder="Google"
                            />
                          </div>
                          <div>
                            <label className="label text-xs">Job Title</label>
                            <input
                              type="text"
                              value={work.job_title}
                              onChange={(e) => updateWorkExperience(index, 'job_title', e.target.value)}
                              className="input text-sm"
                              placeholder="Software Engineer"
                            />
                          </div>
                          <div>
                            <label className="label text-xs">Work Style</label>
                            <select
                              value={work.work_style}
                              onChange={(e) => updateWorkExperience(index, 'work_style', e.target.value)}
                              className="input text-sm"
                            >
                              <option value="onsite">Onsite</option>
                              <option value="hybrid">Hybrid</option>
                              <option value="remote">Remote</option>
                            </select>
                          </div>
                          <div className="grid grid-cols-2 gap-2">
                            <div>
                              <label className="label text-xs">From</label>
                              <input
                                type="month"
                                value={work.start_date}
                                onChange={(e) => updateWorkExperience(index, 'start_date', e.target.value)}
                                className="input text-sm"
                              />
                            </div>
                            <div>
                              <label className="label text-xs">To</label>
                              <input
                                type="month"
                                value={work.end_date || ''}
                                onChange={(e) => updateWorkExperience(index, 'end_date', e.target.value)}
                                className="input text-sm"
                                placeholder="Present"
                              />
                            </div>
                          </div>
                        </div>

                        {/* Row 2: Address */}
                        <div className="grid grid-cols-2 sm:grid-cols-6 gap-3">
                          <div className="sm:col-span-2">
                            <label className="label text-xs">Address 1</label>
                            <input
                              type="text"
                              value={work.address_1 || ''}
                              onChange={(e) => updateWorkExperience(index, 'address_1', e.target.value)}
                              className="input text-sm"
                              placeholder="123 Main St"
                            />
                          </div>
                          <div>
                            <label className="label text-xs">Address 2</label>
                            <input
                              type="text"
                              value={work.address_2 || ''}
                              onChange={(e) => updateWorkExperience(index, 'address_2', e.target.value)}
                              className="input text-sm"
                              placeholder="Suite 100"
                            />
                          </div>
                          <div>
                            <label className="label text-xs">City</label>
                            <input
                              type="text"
                              value={work.city || ''}
                              onChange={(e) => updateWorkExperience(index, 'city', e.target.value)}
                              className="input text-sm"
                              placeholder="Mountain View"
                            />
                          </div>
                          <div>
                            <label className="label text-xs">State</label>
                            <input
                              type="text"
                              value={work.state || ''}
                              onChange={(e) => updateWorkExperience(index, 'state', e.target.value)}
                              className="input text-sm"
                              placeholder="CA"
                            />
                          </div>
                          <div>
                            <label className="label text-xs">Country</label>
                            <input
                              type="text"
                              value={work.country || ''}
                              onChange={(e) => updateWorkExperience(index, 'country', e.target.value)}
                              className="input text-sm"
                              placeholder="USA"
                            />
                          </div>
                        </div>

                        {/* Row 3: Documents */}
                        <div>
                          <label className="label text-xs">Project Documents</label>
                          <p className="text-xs text-surface-500 mb-2">
                            Upload documents about your work at this company for tailored resume generation
                          </p>
                          <WorkDocumentUpload 
                            profileId={selectedProfile?.id} 
                            workIndex={index}
                            savedWorkCount={selectedProfile?.work_experience?.length || 0}
                            onUploadSuccess={(updatedWorkExp) => {
                              // Update local formData with new document paths
                              setFormData(prev => {
                                const work = [...(prev.work_experience || [])]
                                if (work[index]) {
                                  work[index] = { ...work[index], document_paths: updatedWorkExp.document_paths }
                                }
                                return { ...prev, work_experience: work }
                              })
                            }}
                          />
                          {work.document_paths && work.document_paths.length > 0 && (
                            <div className="mt-3 space-y-2">
                              <p className="text-xs text-surface-500">Uploaded documents (click to view content):</p>
                              <div className="flex flex-wrap gap-2">
                                {work.document_paths.map((path, docIndex) => (
                                  <div 
                                    key={docIndex} 
                                    className="flex items-center gap-2 px-3 py-1.5 bg-surface-800 rounded-lg border border-surface-700 group hover:border-primary-500/50 transition-all"
                                  >
                                    <FileText className="w-4 h-4 text-primary-400" />
                                    <button
                                      onClick={() => viewDocumentContent(index, path)}
                                      className="text-xs text-surface-300 hover:text-primary-400 transition-colors cursor-pointer"
                                      title="Click to view document content"
                                    >
                                      {path.split(/[/\\]/).pop()}
                                    </button>
                                    <button
                                      onClick={async (e) => {
                                        e.stopPropagation()
                                        if (!selectedProfile?.id) return
                                        try {
                                          const result = await profileApi.deleteWorkDocument(selectedProfile.id, index, path)
                                          // Update local formData state with the returned document_paths
                                          setFormData(prev => {
                                            const workList = [...(prev.work_experience || [])]
                                            if (workList[index]) {
                                              workList[index] = {
                                                ...workList[index],
                                                document_paths: result.document_paths
                                              }
                                            }
                                            return { ...prev, work_experience: workList }
                                          })
                                          // Also refresh the profile from server to sync selectedProfile
                                          await fetchProfile(selectedProfile.id)
                                          toast.success('Document deleted')
                                        } catch {
                                          toast.error('Failed to delete document')
                                        }
                                      }}
                                      className="p-1 rounded hover:bg-red-500/20 text-surface-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all"
                                      title="Delete document"
                                    >
                                      <X className="w-3 h-3" />
                                    </button>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}

                    <button
                      onClick={addWorkExperience}
                      className="btn-secondary w-full"
                    >
                      <Plus className="w-4 h-4" />
                      Add Work Experience
                    </button>
                  </div>
                )}
              </div>

              {/* ================================================ */}
              {/* SECTION 3: EDUCATION */}
              {/* ================================================ */}
              <div className="card bg-surface-800/50">
                <button
                  onClick={() => toggleSection('education')}
                  className="w-full p-4 flex items-center justify-between text-left"
                >
                  <div className="flex items-center gap-3">
                    <GraduationCap className="w-5 h-5 text-emerald-400" />
                    <span className="font-medium text-white">Education</span>
                    <span className="text-xs text-surface-500">
                      ({(formData.education || []).length} entries)
                    </span>
                  </div>
                  {expandedSections.education ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                </button>

                {expandedSections.education && (
                  <div className="p-4 pt-0 space-y-4">
                    {(formData.education || []).map((edu, index) => (
                      <div key={index} className="p-4 bg-surface-900 rounded-lg space-y-4">
                        <div className="flex items-center justify-between">
                          <h4 className="text-sm font-medium text-white">
                            Education #{index + 1}
                          </h4>
                          <button
                            onClick={() => removeEducation(index)}
                            className="p-1 text-red-400 hover:text-red-300"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>

                        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                          <div className="sm:col-span-2">
                            <label className="label text-xs">University Name</label>
                            <input
                              type="text"
                              value={edu.university_name}
                              onChange={(e) => updateEducation(index, 'university_name', e.target.value)}
                              className="input text-sm"
                              placeholder="Stanford University"
                            />
                          </div>
                          <div>
                            <label className="label text-xs">Degree</label>
                            <input
                              type="text"
                              value={edu.degree}
                              onChange={(e) => updateEducation(index, 'degree', e.target.value)}
                              className="input text-sm"
                              placeholder="Bachelor's"
                            />
                          </div>
                          <div>
                            <label className="label text-xs">Major</label>
                            <input
                              type="text"
                              value={edu.major || ''}
                              onChange={(e) => updateEducation(index, 'major', e.target.value)}
                              className="input text-sm"
                              placeholder="Computer Science"
                            />
                          </div>
                          <div>
                            <label className="label text-xs">Location</label>
                            <input
                              type="text"
                              value={edu.location || ''}
                              onChange={(e) => updateEducation(index, 'location', e.target.value)}
                              className="input text-sm"
                              placeholder="Stanford, CA"
                            />
                          </div>
                        </div>

                        <div className="grid grid-cols-2 gap-3 max-w-xs">
                          <div>
                            <label className="label text-xs">From</label>
                            <input
                              type="month"
                              value={edu.start_date || ''}
                              onChange={(e) => updateEducation(index, 'start_date', e.target.value)}
                              className="input text-sm"
                            />
                          </div>
                          <div>
                            <label className="label text-xs">To</label>
                            <input
                              type="month"
                              value={edu.end_date || ''}
                              onChange={(e) => updateEducation(index, 'end_date', e.target.value)}
                              className="input text-sm"
                            />
                          </div>
                        </div>
                      </div>
                    ))}

                    <button
                      onClick={addEducation}
                      className="btn-secondary w-full"
                    >
                      <Plus className="w-4 h-4" />
                      Add Education
                    </button>
                  </div>
                )}
              </div>

              {/* ================================================ */}
              {/* SECTION 4: AI CUSTOMIZATION */}
              {/* ================================================ */}
              <div className="card bg-surface-800/50">
                <button
                  onClick={() => toggleSection('aiCustomization')}
                  className="w-full p-4 flex items-center justify-between text-left"
                >
                  <div className="flex items-center gap-3">
                    <Brain className="w-5 h-5 text-purple-400" />
                    <span className="font-medium text-white">AI Customization</span>
                    <span className="text-xs text-surface-500">(Optional)</span>
                  </div>
                  {expandedSections.aiCustomization ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                </button>

                {expandedSections.aiCustomization && (
                  <div className="p-4 pt-0 space-y-4">
                    <p className="text-xs text-surface-500">
                      Customize how AI generates content for this profile. These override global settings.
                    </p>

                    {/* Personal Brand */}
                    <div>
                      <label className="label flex items-center gap-2">
                        <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                        Personal Brand Statement
                      </label>
                      <textarea
                        value={formData.personal_brand || ''}
                        onChange={(e) => setFormData({ ...formData, personal_brand: e.target.value })}
                        className="input min-h-[80px] text-sm"
                        placeholder="A brief statement about your professional identity, values, and what makes you unique..."
                      />
                    </div>

                    {/* Key Achievements */}
                    <div>
                      <label className="label flex items-center gap-2">
                        <Target className="w-3.5 h-3.5 text-emerald-400" />
                        Key Achievements (one per line)
                      </label>
                      <textarea
                        value={(formData.key_achievements || []).join('\n')}
                        onChange={(e) => setFormData({ 
                          ...formData, 
                          key_achievements: e.target.value.split('\n').filter(a => a.trim()) 
                        })}
                        className="input min-h-[80px] text-sm"
                        placeholder="Led team of 10 engineers...&#10;Increased revenue by 50%...&#10;Launched product used by 1M+ users..."
                      />
                    </div>

                    {/* Priority Skills & Target Roles */}
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="label text-xs">Priority Skills (comma separated)</label>
                        <input
                          type="text"
                          value={(formData.priority_skills || []).join(', ')}
                          onChange={(e) => setFormData({ 
                            ...formData, 
                            priority_skills: e.target.value.split(',').map(s => s.trim()).filter(Boolean) 
                          })}
                          className="input text-sm"
                          placeholder="Python, React, AWS, Leadership"
                        />
                      </div>
                      <div>
                        <label className="label text-xs">Target Roles (comma separated)</label>
                        <input
                          type="text"
                          value={(formData.target_roles || []).join(', ')}
                          onChange={(e) => setFormData({ 
                            ...formData, 
                            target_roles: e.target.value.split(',').map(s => s.trim()).filter(Boolean) 
                          })}
                          className="input text-sm"
                          placeholder="Senior Engineer, Tech Lead, CTO"
                        />
                      </div>
                    </div>

                    {/* Target Industries */}
                    <div>
                      <label className="label text-xs">Target Industries (comma separated)</label>
                      <input
                        type="text"
                        value={(formData.target_industries || []).join(', ')}
                        onChange={(e) => setFormData({ 
                          ...formData, 
                          target_industries: e.target.value.split(',').map(s => s.trim()).filter(Boolean) 
                        })}
                        className="input text-sm"
                        placeholder="Fintech, Healthcare, AI/ML, SaaS"
                      />
                    </div>

                    {/* Resume Tone Override */}
                    <div>
                      <label className="label text-xs">Resume Tone Override</label>
                      <select
                        value={formData.resume_tone_override || ''}
                        onChange={(e) => setFormData({ ...formData, resume_tone_override: e.target.value })}
                        className="input text-sm"
                      >
                        <option value="">Use Global Setting</option>
                        <option value="professional">Professional</option>
                        <option value="creative">Creative</option>
                        <option value="technical">Technical</option>
                        <option value="executive">Executive</option>
                      </select>
                    </div>

                    {/* Salary Expectations */}
                    <div>
                      <label className="label flex items-center gap-2">
                        <DollarSign className="w-3.5 h-3.5 text-emerald-400" />
                        Salary Expectations
                      </label>
                      <div className="flex items-center gap-3">
                        <select
                          value={formData.salary_currency || 'USD'}
                          onChange={(e) => setFormData({ ...formData, salary_currency: e.target.value })}
                          className="input text-sm w-24"
                        >
                          <option value="USD">USD</option>
                          <option value="EUR">EUR</option>
                          <option value="GBP">GBP</option>
                          <option value="CAD">CAD</option>
                          <option value="AUD">AUD</option>
                        </select>
                        <input
                          type="number"
                          value={formData.salary_min || ''}
                          onChange={(e) => setFormData({ ...formData, salary_min: parseInt(e.target.value) || undefined })}
                          className="input text-sm flex-1"
                          placeholder="Min (e.g. 80000)"
                        />
                        <span className="text-surface-500">to</span>
                        <input
                          type="number"
                          value={formData.salary_max || ''}
                          onChange={(e) => setFormData({ ...formData, salary_max: parseInt(e.target.value) || undefined })}
                          className="input text-sm flex-1"
                          placeholder="Max (e.g. 120000)"
                        />
                      </div>
                      <p className="text-xs text-surface-500 mt-1">Used for answering salary expectation questions</p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-6 border-t border-surface-800 flex justify-end gap-3 sticky bottom-0 bg-surface-900">
              <button 
                onClick={handleCloseModal}
                className="btn-secondary"
              >
                Cancel
              </button>
              <button 
                onClick={handleSubmit}
                disabled={isLoading}
                className="btn-primary"
              >
                {isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
                {isEditing ? 'Save Changes' : 'Create Profile'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Document Content Viewer Modal */}
      {showDocumentViewer && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-[60] flex items-center justify-center p-4">
          <div className="card w-full max-w-4xl max-h-[85vh] flex flex-col animate-slide-up">
            {/* Modal Header */}
            <div className="p-4 border-b border-surface-800 flex items-center justify-between flex-shrink-0">
              <div className="flex items-center gap-3">
                <FileText className="w-5 h-5 text-primary-400" />
                <div>
                  <h3 className="font-semibold text-white">
                    {documentViewerContent?.filename || 'Document Content'}
                  </h3>
                  {documentViewerContent?.format_type && (
                    <span className="text-xs text-surface-500 uppercase">
                      {documentViewerContent.format_type} format
                    </span>
                  )}
                </div>
              </div>
              <button 
                onClick={() => {
                  setShowDocumentViewer(false)
                  setDocumentViewerContent(null)
                }}
                className="p-2 rounded-lg hover:bg-surface-800"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Content */}
            <div className="flex-1 overflow-auto p-4">
              {documentViewerLoading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-8 h-8 animate-spin text-primary-400" />
                  <span className="ml-3 text-surface-400">Parsing document...</span>
                </div>
              ) : documentViewerContent?.content ? (
                <div className="bg-surface-800/50 rounded-lg p-4 border border-surface-700">
                  <pre className="text-sm text-surface-300 whitespace-pre-wrap font-mono leading-relaxed overflow-x-auto">
                    {documentViewerContent.content}
                  </pre>
                </div>
              ) : (
                <div className="text-center py-12 text-surface-500">
                  No content available
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-surface-800 flex justify-between items-center flex-shrink-0">
              <div className="text-xs text-surface-500">
                {documentViewerContent?.content && (
                  <span>{documentViewerContent.content.length.toLocaleString()} characters</span>
                )}
              </div>
              <button 
                onClick={() => {
                  setShowDocumentViewer(false)
                  setDocumentViewerContent(null)
                }}
                className="btn-secondary"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Resume Viewer Modal */}
      {showResumeViewer && resumeViewerUrl && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-[60] flex items-center justify-center p-4">
          <div className="card w-full max-w-5xl h-[90vh] flex flex-col animate-slide-up">
            <div className="p-4 border-b border-surface-800 flex items-center justify-between flex-shrink-0">
              <div className="flex items-center gap-3">
                <FileText className="w-5 h-5 text-primary-400" />
                <h3 className="font-semibold text-white">{resumeViewerFilename}</h3>
              </div>
              <button 
                onClick={() => {
                  setShowResumeViewer(false)
                  setResumeViewerUrl(null)
                }}
                className="p-2 rounded-lg hover:bg-surface-800"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="flex-1 overflow-hidden">
              <iframe
                src={resumeViewerUrl}
                className="w-full h-full border-0"
                title={resumeViewerFilename}
              />
            </div>
          </div>
        </div>
      )}

      {/* Cover Letter Generator Modal */}
      {showCoverLetterGenerator && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-[60] flex items-center justify-center p-4">
          <div className="card w-full max-w-5xl h-[90vh] flex flex-col animate-slide-up">
            <div className="p-4 border-b border-surface-800 flex items-center justify-between flex-shrink-0">
              <div className="flex items-center gap-3">
                <FileText className="w-5 h-5 text-purple-400" />
                <h3 className="font-semibold text-white">Test Cover Letter Generation</h3>
              </div>
              <button 
                onClick={closeCoverLetterGenerator}
                className="p-2 rounded-lg hover:bg-surface-800"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            {generatedCoverLetterUrl ? (
              <div className="flex-1 overflow-hidden flex flex-col">
                <div className="flex-1 overflow-hidden">
                  <iframe
                    src={generatedCoverLetterUrl}
                    className="w-full h-full border-0"
                    title="Generated Cover Letter"
                  />
                </div>
                <div className="p-4 border-t border-surface-800 flex justify-end gap-3">
                  <button
                    onClick={async () => {
                      if (generatedCoverLetterId && selectedProfile?.id) {
                        try {
                          await profileApi.deleteGeneratedCoverLetter(selectedProfile.id, generatedCoverLetterId)
                        } catch {
                          // Ignore cleanup errors
                        }
                      }
                      setGeneratedCoverLetterUrl(null)
                      setGeneratedCoverLetterId(null)
                    }}
                    className="btn-secondary"
                  >
                    Generate Another
                  </button>
                  <button
                    onClick={closeCoverLetterGenerator}
                    className="btn-primary"
                  >
                    Close
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex-1 overflow-hidden flex flex-col p-4">
                <div className="flex-1 flex flex-col">
                  <label className="label mb-2">Cover Letter Content</label>
                  <textarea
                    value={coverLetterContent}
                    onChange={(e) => setCoverLetterContent(e.target.value)}
                    className="input flex-1 min-h-[300px] resize-none font-mono text-sm"
                    placeholder="Enter the cover letter content that will replace {{content}} in your template..."
                  />
                </div>
                <div className="pt-4 flex justify-end gap-3">
                  <button
                    onClick={closeCoverLetterGenerator}
                    className="btn-secondary"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleGenerateCoverLetter}
                    disabled={!coverLetterContent.trim() || coverLetterGenerating}
                    className="btn-primary"
                  >
                    {coverLetterGenerating ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Converting...
                      </>
                    ) : (
                      'Convert Cover Letter'
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
