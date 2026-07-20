import React, { useState, useEffect } from 'react';
import { 
  Calendar, MapPin, User, Lock, Mail, Plus, Search, Trash2, 
  Edit, CheckCircle, XCircle, LogOut, Ticket, PlusCircle, 
  Sparkles, Clock, ArrowLeft, ShieldCheck, Loader, Check, AlertCircle
} from 'lucide-react';

const API_BASE = window.location.port === "3000" 
  ? "http://localhost:8000" 
  : "http://localhost:8001";

// --- INTERFACES ---
interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  is_admin: boolean;
  created_at: string;
}

interface EventItem {
  id: string;
  title: string;
  description: string | null;
  location: string | null;
  image_url: string | null;
  starts_at: string;
  ends_at: string;
  capacity: number;
  price: string;
  is_published: boolean;
  spots_remaining: number;
  created_at: string;
}

interface TicketItem {
  id: string;
  registration_id: string;
  ticket_code: string;
  qr_image_url: string | null;
  is_used: boolean;
  used_at: string | null;
  issued_at: string;
  event: {
    id: string;
    title: string;
    location: string | null;
    starts_at: string;
    ends_at: string;
    price: string;
  } | null;
}

// --- DETERMINISTIC QR CODE COMPONENT ---
const TicketQRCode = ({ code }: { code: string }) => {
  // Simple hashing to build a deterministic grid pattern
  const hash = Array.from(code).reduce((acc, char) => acc + char.charCodeAt(0), 0);
  const grid: boolean[][] = [];
  for (let i = 0; i < 10; i++) {
    const row: boolean[] = [];
    for (let j = 0; j < 10; j++) {
      const active = ((hash + (i * 7) + (j * 13)) % 3 === 0) || 
                     ((i === 0 || i === 9 || j === 0 || j === 9) && (i !== 4 && j !== 4));
      row.push(active);
    }
    grid.push(row);
  }

  return (
    <div style={{ background: 'white', padding: '10px', borderRadius: '8px', display: 'inline-block' }}>
      <svg width="110" height="110" viewBox="0 0 10 10" style={{ display: 'block' }}>
        {/* Top-Left Target */}
        <rect x="0" y="0" width="3" height="3" fill="#0a0e1a" />
        <rect x="0.4" y="0.4" width="2.2" height="2.2" fill="white" />
        <rect x="0.8" y="0.8" width="1.4" height="1.4" fill="#0a0e1a" />

        {/* Top-Right Target */}
        <rect x="7" y="0" width="3" height="3" fill="#0a0e1a" />
        <rect x="7.4" y="0.4" width="2.2" height="2.2" fill="white" />
        <rect x="7.8" y="0.8" width="1.4" height="1.4" fill="#0a0e1a" />

        {/* Bottom-Left Target */}
        <rect x="0" y="7" width="3" height="3" fill="#0a0e1a" />
        <rect x="0.4" y="7.4" width="2.2" height="2.2" fill="white" />
        <rect x="0.8" y="7.8" width="1.4" height="1.4" fill="#0a0e1a" />

        {/* Matrix Grid Pattern */}
        {grid.map((row, r) => 
          row.map((active, c) => {
            // Skip the main alignment target corners
            if ((r < 3 && c < 3) || (r < 3 && c > 6) || (r > 6 && c < 3)) return null;
            return active ? (
              <rect key={`${r}-${c}`} x={c} y={r} width="1" height="1" fill="#0a0e1a" />
            ) : null;
          })
        )}
      </svg>
    </div>
  );
};

// --- MAIN APP COMPONENT ---
function App() {
  // Navigation & Core States
  const [token, setToken] = useState<string | null>(localStorage.getItem("token"));
  const [user, setUser] = useState<UserProfile | null>(null);
  const [currentView, setCurrentView] = useState<string>('events');
  const [loading, setLoading] = useState<boolean>(false);
  const [authLoading, setAuthLoading] = useState<boolean>(true);

  // Data States
  const [events, setEvents] = useState<EventItem[]>([]);
  const [adminEvents, setAdminEvents] = useState<EventItem[]>([]);
  const [myTickets, setMyTickets] = useState<TicketItem[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<EventItem | null>(null);

  // Search & Filter
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [priceFilter, setPriceFilter] = useState<'all' | 'free' | 'paid'>('all');

  // Auth Inputs
  const [email, setEmail] = useState<string>('');
  const [fullName, setFullName] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  
  // Notification banner
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Admin Forms State
  const [eventTitle, setEventTitle] = useState<string>('');
  const [eventDescription, setEventDescription] = useState<string>('');
  const [eventLocation, setEventLocation] = useState<string>('');
  const [eventStartsAt, setEventStartsAt] = useState<string>('');
  const [eventEndsAt, setEventEndsAt] = useState<string>('');
  const [eventCapacity, setEventCapacity] = useState<number>(100);
  const [eventPrice, setEventPrice] = useState<string>('0.00');
  const [eventIsPublished, setEventIsPublished] = useState<boolean>(true);
  const [editEventId, setEditEventId] = useState<string | null>(null);

  // Ticket Validation State
  const [validateCode, setValidateCode] = useState<string>('');
  const [validationResult, setValidationResult] = useState<{
    valid: boolean;
    message: string;
    ticket?: TicketItem;
  } | null>(null);

  // --- FLOATING NOTIFICATION HANDLER ---
  const triggerNotification = (type: 'success' | 'error', text: string) => {
    setNotification({ type, text });
    setTimeout(() => {
      setNotification(null);
    }, 4000);
  };

  // --- API CALL UTILITIES ---
  const getAuthHeaders = () => {
    return {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`
    };
  };

  // Fetch current user details
  const fetchUserProfile = async (authToken: string) => {
    try {
      const response = await fetch(`${API_BASE}/auth/me`, {
        headers: { "Authorization": `Bearer ${authToken}` }
      });
      if (response.ok) {
        const data = await response.json();
        setUser(data);
      } else {
        // Expired or bad token
        handleLogout();
      }
    } catch (e) {
      handleLogout();
    } finally {
      setAuthLoading(false);
    }
  };

  // Fetch all published events (for public browsing)
  const fetchEvents = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/events`);
      if (response.ok) {
        const data = await response.json();
        setEvents(data.items);
      }
    } catch (e) {
      triggerNotification('error', "Could not fetch events from server.");
    } finally {
      setLoading(false);
    }
  };

  // Fetch all events including drafts (admin only)
  const fetchAdminEvents = async () => {
    if (!user?.is_admin || !token) return;
    try {
      const response = await fetch(`${API_BASE}/events/admin/all`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const data = await response.json();
        setAdminEvents(data.items);
      }
    } catch (e) {}
  };

  // Fetch current user's tickets
  const fetchMyTickets = async () => {
    if (!token) return;
    try {
      const response = await fetch(`${API_BASE}/tickets/users/me/tickets`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const data = await response.json();
        setMyTickets(data);
      }
    } catch (e) {
      triggerNotification('error', "Could not retrieve your tickets.");
    }
  };

  // --- INITIAL COMPONENT MOUNT EFFECT ---
  useEffect(() => {
    fetchEvents();
    if (token) {
      fetchUserProfile(token);
      fetchMyTickets();
    } else {
      setAuthLoading(false);
    }
  }, [token]);

  // Fetch admin events when admin views it
  useEffect(() => {
    if (user?.is_admin) {
      fetchAdminEvents();
    }
  }, [user, currentView]);

  // --- AUTH ACTIONS ---
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      triggerNotification('error', "Please fill in all credentials.");
      return;
    }
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      });
      if (response.ok) {
        const data = await response.json();
        localStorage.setItem("token", data.access_token);
        setToken(data.access_token);
        triggerNotification('success', "Welcome back! Login successful.");
        setCurrentView('events');
        // Reset forms
        setEmail('');
        setPassword('');
      } else {
        const errorData = await response.json();
        triggerNotification('error', errorData.detail || "Invalid email or password.");
      }
    } catch (e) {
      triggerNotification('error', "Server connection error.");
    } finally {
      setLoading(false);
    }
  };

  const handleRegisterUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !fullName || !password) {
      triggerNotification('error', "Please enter all registration details.");
      return;
    }
    if (password.length < 8) {
      triggerNotification('error', "Password must be at least 8 characters long.");
      return;
    }
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, full_name: fullName, password })
      });
      if (response.ok) {
        triggerNotification('success', "Account registered! You can now log in.");
        // Switch to login
        setFullName('');
        setPassword('');
        setEmail(email); // preserve email
        setCurrentView('login');
      } else {
        const errorData = await response.json();
        triggerNotification('error', errorData.detail || "Email already in use.");
      }
    } catch (e) {
      triggerNotification('error', "Registration server connection failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    setToken(null);
    setUser(null);
    setMyTickets([]);
    triggerNotification('success', "Logged out. Goodbye!");
    setCurrentView('events');
  };

  // --- EVENT REGISTRATION ---
  const handleRegisterForEvent = async (eventId: string) => {
    if (!token) {
      triggerNotification('error', "You must login to register for events.");
      setCurrentView('login');
      return;
    }
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/events/${eventId}/register`, {
        method: "POST",
        headers: getAuthHeaders()
      });
      if (response.ok) {
        triggerNotification('success', "Registered successfully! Ticket issued.");
        fetchEvents(); // reload capacities
        fetchMyTickets(); // reload user tickets
        setCurrentView('my-tickets');
      } else {
        const err = await response.json();
        triggerNotification('error', err.detail || "Unable to register for event.");
      }
    } catch (e) {
      triggerNotification('error', "Failed to complete event registration.");
    } finally {
      setLoading(false);
    }
  };

  // --- ADMIN ACTIONS ---
  const handleCreateOrUpdateEvent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!eventTitle || !eventStartsAt || !eventEndsAt || eventCapacity <= 0) {
      triggerNotification('error', "Please fill in all required event details.");
      return;
    }

    const payload = {
      title: eventTitle,
      description: eventDescription || null,
      location: eventLocation || null,
      starts_at: new Date(eventStartsAt).toISOString(),
      ends_at: new Date(eventEndsAt).toISOString(),
      capacity: eventCapacity,
      price: parseFloat(eventPrice) || 0.00
    };

    setLoading(true);
    try {
      let url = `${API_BASE}/events`;
      let method = "POST";
      
      if (editEventId) {
        url = `${API_BASE}/events/${editEventId}`;
        method = "PUT";
      }

      const response = await fetch(url, {
        method: method,
        headers: getAuthHeaders(),
        body: JSON.stringify(payload)
      });

      if (response.ok) {
        triggerNotification('success', editEventId ? "Event updated successfully." : "Event created successfully.");
        // If we updated, we might also want to set published status
        if (editEventId) {
          // Send separate published toggle if modified
          await fetch(`${API_BASE}/events/${editEventId}`, {
            method: "PUT",
            headers: getAuthHeaders(),
            body: JSON.stringify({ is_published: eventIsPublished })
          });
        }
        
        // Reset Form
        setEventTitle('');
        setEventDescription('');
        setEventLocation('');
        setEventStartsAt('');
        setEventEndsAt('');
        setEventCapacity(100);
        setEventPrice('0.00');
        setEventIsPublished(true);
        setEditEventId(null);
        
        fetchEvents();
        fetchAdminEvents();
        setCurrentView('admin-events');
      } else {
        const err = await response.json();
        triggerNotification('error', err.detail || "Failed to save event.");
      }
    } catch (e) {
      triggerNotification('error', "Admin API communication failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleEditClick = (event: EventItem) => {
    setEditEventId(event.id);
    setEventTitle(event.title);
    setEventDescription(event.description || '');
    setEventLocation(event.location || '');
    
    // Format dates back for input type datetime-local
    const formatForInput = (isoStr: string) => {
      const d = new Date(isoStr);
      const pad = (n: number) => n.toString().padStart(2, '0');
      return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
    };
    
    setEventStartsAt(formatForInput(event.starts_at));
    setEventEndsAt(formatForInput(event.ends_at));
    setEventCapacity(event.capacity);
    setEventPrice(event.price);
    setEventIsPublished(event.is_published);
    setCurrentView('admin-form');
  };

  const handleDeleteEvent = async (eventId: string) => {
    if (!window.confirm("Are you sure you want to delete this event? This will remove all bookings.")) return;
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/events/${eventId}`, {
        method: "DELETE",
        headers: getAuthHeaders()
      });
      if (response.ok) {
        triggerNotification('success', "Event deleted.");
        fetchEvents();
        fetchAdminEvents();
      } else {
        triggerNotification('error', "Could not delete event.");
      }
    } catch (e) {
      triggerNotification('error', "Error connecting to server.");
    } finally {
      setLoading(false);
    }
  };

  // --- TICKET VALIDATION ---
  const handleValidateTicket = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateCode.trim()) {
      triggerNotification('error', "Please enter a valid ticket code.");
      return;
    }
    setLoading(true);
    setValidationResult(null);
    try {
      const response = await fetch(`${API_BASE}/tickets/${validateCode.trim()}/validate`, {
        method: "POST",
        headers: getAuthHeaders()
      });
      const data = await response.json();
      if (response.ok) {
        setValidationResult({
          valid: data.valid,
          message: data.message,
          ticket: data.ticket
        });
        if (data.valid) {
          triggerNotification('success', "Access GRANTED! Attendee checked in.");
        } else {
          triggerNotification('error', data.message || "Ticket is invalid or already used.");
        }
      } else {
        setValidationResult({
          valid: false,
          message: data.detail || "Ticket code not found in system."
        });
        triggerNotification('error', data.detail || "Ticket code not found.");
      }
    } catch (e) {
      triggerNotification('error', "Error validating ticket on server.");
    } finally {
      setLoading(false);
    }
  };

  // --- DATE HELPER ---
  const formatDate = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch (e) {
      return dateStr;
    }
  };

  // --- FILTERS & SEARCH PROCESS ---
  const filteredEvents = events.filter(evt => {
    const matchesSearch = 
      evt.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
      (evt.location && evt.location.toLowerCase().includes(searchQuery.toLowerCase()));
    
    const isFree = parseFloat(evt.price) === 0;
    if (priceFilter === 'free') return matchesSearch && isFree;
    if (priceFilter === 'paid') return matchesSearch && !isFree;
    return matchesSearch;
  });

  return (
    <>
      {/* Reworked design - No brand gradient definition */}

      {/* Floating alert banners */}
      {notification && (
        <div className={`notification-banner ${notification.type === 'success' ? 'notification-success' : 'notification-error'}`}>
          {notification.type === 'success' ? <CheckCircle size={18} /> : <AlertCircle size={18} />}
          <span style={{ fontSize: '0.9rem', fontWeight: 600 }}>{notification.text}</span>
        </div>
      )}

      {/* Navigation Header */}
      <header className="navbar glass-panel">
        <div className="navbar-brand" onClick={() => { setCurrentView('events'); setSelectedEvent(null); }}>
          <Ticket size={24} style={{ transform: 'rotate(-10deg)' }} />
          <span>AlphaPass</span>
        </div>

        <nav className="navbar-menu">
          <div 
            className={`navbar-link ${currentView === 'events' || currentView === 'event-detail' ? 'active' : ''}`}
            onClick={() => { setCurrentView('events'); setSelectedEvent(null); }}
          >
            <Calendar size={16} />
            <span>Browse Events</span>
          </div>

          {token && (
            <div 
              className={`navbar-link ${currentView === 'my-tickets' ? 'active' : ''}`}
              onClick={() => { setCurrentView('my-tickets'); fetchMyTickets(); }}
            >
              <Ticket size={16} />
              <span>My Tickets</span>
            </div>
          )}

          {user?.is_admin && (
            <>
              <div 
                className={`navbar-link ${currentView === 'admin-events' || currentView === 'admin-form' ? 'active' : ''}`}
                onClick={() => setCurrentView('admin-events')}
              >
                <PlusCircle size={16} />
                <span>Admin Panel</span>
              </div>
              <div 
                className={`navbar-link ${currentView === 'admin-validate' ? 'active' : ''}`}
                onClick={() => { setCurrentView('admin-validate'); setValidationResult(null); setValidateCode(''); }}
              >
                <ShieldCheck size={16} />
                <span>Validator</span>
              </div>
            </>
          )}
        </nav>

        <div className="navbar-user">
          {authLoading ? (
            <Loader size={16} className="spinner" style={{ borderTopColor: '#6366f1' }} />
          ) : user ? (
            <>
              <div className="user-badge">
                <span className="user-name">{user.full_name}</span>
                <span className="user-role">{user.is_admin ? "Administrator" : "Attendee"}</span>
              </div>
              <button className="btn btn-secondary" style={{ padding: '8px 12px' }} onClick={handleLogout} title="Log Out">
                <LogOut size={16} />
              </button>
            </>
          ) : (
            <div style={{ display: 'flex', gap: '8px' }}>
              <button 
                className="btn btn-outline" 
                style={{ padding: '8px 16px', fontSize: '0.85rem' }} 
                onClick={() => setCurrentView('login')}
              >
                Sign In
              </button>
              <button 
                className="btn btn-primary" 
                style={{ padding: '8px 16px', fontSize: '0.85rem' }} 
                onClick={() => setCurrentView('register')}
              >
                Register
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Main Container */}
      <main className="main-content">
        
        {/* --- VIEW 1: EVENTS GALLERY --- */}
        {currentView === 'events' && (
          <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
            <section className="hero-banner">
              <h1 className="hero-title">Experience the Best Events</h1>
              <p className="hero-subtitle">
                Secure your spots at top conferences, concerts, and workshops with instant digital tickets and seamless check-in.
              </p>
              <div style={{ display: 'flex', justifyContent: 'center' }}>
                <span className="badge badge-indigo" style={{ display: 'inline-flex', padding: '6px 14px', borderRadius: '20px' }}>
                  <Sparkles size={14} style={{ marginRight: '6px' }} />
                  Powered by AWS and FastAPI
                </span>
              </div>
            </section>

            {/* Filter controls */}
            <div className="filter-bar">
              <div className="search-input-wrapper">
                <Search size={18} className="search-icon" />
                <input 
                  type="text" 
                  className="search-input" 
                  placeholder="Search events by title or location..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>

              <div className="tab-group">
                <button 
                  className={`tab-btn ${priceFilter === 'all' ? 'active' : ''}`}
                  onClick={() => setPriceFilter('all')}
                >
                  All
                </button>
                <button 
                  className={`tab-btn ${priceFilter === 'free' ? 'active' : ''}`}
                  onClick={() => setPriceFilter('free')}
                >
                  Free
                </button>
                <button 
                  className={`tab-btn ${priceFilter === 'paid' ? 'active' : ''}`}
                  onClick={() => setPriceFilter('paid')}
                >
                  Paid
                </button>
              </div>
            </div>

            {/* Loading Indicator */}
            {loading ? (
              <div style={{ display: 'flex', justifyContent: 'center', padding: '60px 0', flexDirection: 'column', alignItems: 'center', gap: '16px' }}>
                <Loader className="spinner" size={32} />
                <span style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>Fetching events...</span>
              </div>
            ) : filteredEvents.length > 0 ? (
              <div className="events-grid">
                {filteredEvents.map((evt) => {
                  const percentFilled = Math.min(100, Math.round(((evt.capacity - evt.spots_remaining) / evt.capacity) * 100));
                  return (
                    <div 
                      key={evt.id} 
                      className="event-card glass-panel"
                      onClick={() => { setSelectedEvent(evt); setCurrentView('event-detail'); }}
                    >
                      <div className="event-image-container">
                        <img 
                          src={evt.image_url || "https://images.unsplash.com/photo-1501281668745-f7f57925c3b4?w=800&auto=format&fit=crop&q=60"} 
                          className="event-image" 
                          alt={evt.title} 
                        />
                        <div className="event-price-overlay">
                          <span className={`badge ${parseFloat(evt.price) === 0 ? 'badge-success' : 'badge-indigo'}`}>
                            {parseFloat(evt.price) === 0 ? "Free" : `$${parseFloat(evt.price).toFixed(2)}`}
                          </span>
                        </div>
                      </div>

                      <div className="event-card-content">
                        <h3 className="event-card-title">{evt.title}</h3>
                        <p className="event-card-desc">{evt.description || "No description provided."}</p>
                        
                        <div className="event-meta-info">
                          <div className="event-meta-item">
                            <Calendar size={14} />
                            <span>{formatDate(evt.starts_at)}</span>
                          </div>
                          {evt.location && (
                            <div className="event-meta-item">
                              <MapPin size={14} />
                              <span>{evt.location}</span>
                            </div>
                          )}
                        </div>

                        <div className="spots-bar-container">
                          <div className="spots-bar-labels">
                            <span style={{ color: evt.spots_remaining === 0 ? 'var(--error)' : 'var(--text-secondary)' }}>
                              {evt.spots_remaining === 0 ? "Fully Booked" : `${evt.spots_remaining} spots left`}
                            </span>
                            <span>{evt.capacity} Max</span>
                          </div>
                          <div className="spots-bar-track">
                            <div 
                              className="spots-bar-fill" 
                              style={{ 
                                width: `${percentFilled}%`,
                                background: evt.spots_remaining === 0 ? 'var(--error)' : 'var(--accent-color)'
                              }}
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="empty-state glass-panel animate-fade-in" style={{ padding: '60px 24px' }}>
                <Search size={40} className="empty-icon" />
                <h3 style={{ fontSize: '1.25rem', marginBottom: '8px' }}>No events found</h3>
                <p style={{ color: 'var(--text-secondary)' }}>Try broadening your keywords or search query.</p>
              </div>
            )}
          </div>
        )}

        {/* --- VIEW 2: EVENT DETAILS VIEW --- */}
        {currentView === 'event-detail' && selectedEvent && (
          <div className="animate-fade-in">
            <button 
              className="btn btn-secondary" 
              style={{ marginBottom: '24px', padding: '10px 18px' }}
              onClick={() => { setCurrentView('events'); setSelectedEvent(null); }}
            >
              <ArrowLeft size={16} />
              <span>Back to Listings</span>
            </button>

            <div className="event-detail-grid">
              {/* Left Column */}
              <div>
                <div className="event-detail-header-img">
                  <img 
                    src={selectedEvent.image_url || "https://images.unsplash.com/photo-1501281668745-f7f57925c3b4?w=800&auto=format&fit=crop&q=60"} 
                    alt={selectedEvent.title} 
                  />
                </div>
                
                <h1 style={{ fontSize: '2.2rem', marginBottom: '16px' }}>{selectedEvent.title}</h1>
                
                <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', marginBottom: '24px' }}>
                  <div className="event-meta-item" style={{ fontSize: '0.95rem' }}>
                    <Calendar size={18} />
                    <span>{formatDate(selectedEvent.starts_at)}</span>
                  </div>
                  {selectedEvent.location && (
                    <div className="event-meta-item" style={{ fontSize: '0.95rem' }}>
                      <MapPin size={18} />
                      <span>{selectedEvent.location}</span>
                    </div>
                  )}
                </div>

                <div className="event-detail-desc">
                  <h3>About this Event</h3>
                  <p style={{ marginTop: '10px', whiteSpace: 'pre-wrap' }}>
                    {selectedEvent.description || "No description provided for this event."}
                  </p>
                </div>
              </div>

              {/* Right Column (Ticket Purchasing Card) */}
              <div className="event-detail-card glass-panel">
                <h3 style={{ fontSize: '1.25rem', marginBottom: '16px', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
                  Ticket Details
                </h3>

                <div className="price-box">
                  <span className="price-box-label">Admission Price:</span>
                  <span className="price-box-amount">
                    {parseFloat(selectedEvent.price) === 0 ? "FREE" : `$${parseFloat(selectedEvent.price).toFixed(2)}`}
                  </span>
                </div>

                <div className="spots-bar-container" style={{ marginBottom: '24px' }}>
                  <div className="spots-bar-labels">
                    <span style={{ fontWeight: 600 }}>Spots Remaining</span>
                    <span>{selectedEvent.spots_remaining} / {selectedEvent.capacity}</span>
                  </div>
                  <div className="spots-bar-track" style={{ height: '8px' }}>
                    <div 
                      className="spots-bar-fill" 
                      style={{ 
                        width: `${Math.min(100, Math.round(((selectedEvent.capacity - selectedEvent.spots_remaining) / selectedEvent.capacity) * 100))}%`,
                        background: selectedEvent.spots_remaining === 0 ? 'var(--error)' : 'var(--accent-color)'
                      }}
                    />
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '0.88rem', color: 'var(--text-secondary)', marginBottom: '24px' }}>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <Clock size={16} style={{ color: 'var(--accent-color)', flexShrink: 0 }} />
                    <span>Ends: {formatDate(selectedEvent.ends_at)}</span>
                  </div>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <ShieldCheck size={16} style={{ color: 'var(--accent-color)', flexShrink: 0 }} />
                    <span>Instant confirmation email with digital QR code ticket.</span>
                  </div>
                </div>

                {token && myTickets.some(t => t.event?.id === selectedEvent.id) ? (
                  <button 
                    className="btn btn-secondary" 
                    style={{ width: '100%', padding: '14px 20px', fontSize: '1.05rem', borderColor: 'var(--success)', color: 'var(--success)' }}
                    onClick={() => setCurrentView('my-tickets')}
                  >
                    <Check size={18} style={{ marginRight: '6px' }} />
                    <span>Registered — View Ticket</span>
                  </button>
                ) : (
                  <button 
                    className="btn btn-primary" 
                    style={{ width: '100%', padding: '14px 20px', fontSize: '1.05rem' }}
                    disabled={selectedEvent.spots_remaining === 0 || loading}
                    onClick={() => handleRegisterForEvent(selectedEvent.id)}
                  >
                    {loading ? (
                      <Loader size={18} className="spinner" />
                    ) : selectedEvent.spots_remaining === 0 ? (
                      "Fully Booked"
                    ) : token ? (
                      "Register & Get Ticket"
                    ) : (
                      "Login to Register"
                    )}
                  </button>
                )}
              </div>
            </div>
          </div>
        )}

        {/* --- VIEW 3: USER TICKETS TAB --- */}
        {currentView === 'my-tickets' && (
          <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            <div style={{ textAlign: 'left' }}>
              <h1 style={{ fontSize: '2rem', marginBottom: '8px' }}>My Tickets</h1>
              <p style={{ color: 'var(--text-secondary)' }}>Your digital entry passes for upcoming registrations. Show the barcode at the door.</p>
            </div>

            {myTickets.length > 0 ? (
              <div className="tickets-list">
                {myTickets.map((t) => (
                  <div key={t.id} className="ticket-stub">
                    <div className="ticket-notch-top"></div>
                    <div className="ticket-notch-bottom"></div>

                    {/* Left Stub Details */}
                    <div className="ticket-left">
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '8px' }}>
                          <span className={`badge ${t.is_used ? 'badge-danger' : 'badge-success'}`}>
                            {t.is_used ? "Checked In" : "Active / Unused"}
                          </span>
                          <span className="ticket-code-badge">CODE: {t.ticket_code.substring(0, 8).toUpperCase()}</span>
                        </div>
                        <h2 className="ticket-event-title" style={{ marginTop: '12px' }}>
                          {t.event?.title || "Unknown Event"}
                        </h2>
                      </div>

                      <div className="ticket-details-grid">
                        <div>
                          <div className="ticket-detail-lbl">Date & Time</div>
                          <div className="ticket-detail-val">
                            {t.event ? formatDate(t.event.starts_at) : "N/A"}
                          </div>
                        </div>
                        <div>
                          <div className="ticket-detail-lbl">Venue</div>
                          <div className="ticket-detail-val">
                            {t.event?.location || "N/A"}
                          </div>
                        </div>
                        <div>
                          <div className="ticket-detail-lbl">Attendee</div>
                          <div className="ticket-detail-val">{user?.full_name}</div>
                        </div>
                        <div>
                          <div className="ticket-detail-lbl">Issued</div>
                          <div className="ticket-detail-val">{formatDate(t.issued_at)}</div>
                        </div>
                      </div>
                    </div>

                    {/* Right Stub Scanning Barcode */}
                    <div className="ticket-right">
                      <TicketQRCode code={t.id} />
                      <span style={{ fontSize: '0.65rem', fontFamily: 'var(--mono-font)', color: 'var(--text-muted)' }}>
                        ID: {t.id}
                      </span>
                      {t.is_used && t.used_at && (
                        <span style={{ fontSize: '0.72rem', color: 'var(--error)', fontWeight: 700 }}>
                          Checked in at {new Date(t.used_at).toLocaleTimeString()}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state glass-panel animate-fade-in" style={{ padding: '80px 24px' }}>
                <Ticket size={48} className="empty-icon" style={{ opacity: 0.5 }} />
                <h3 style={{ fontSize: '1.3rem', marginBottom: '8px' }}>No tickets registered</h3>
                <p style={{ color: 'var(--text-secondary)', marginBottom: '20px' }}>You haven't booked any event registrations yet.</p>
                <button className="btn btn-primary" onClick={() => setCurrentView('events')}>
                  Browse Events Now
                </button>
              </div>
            )}
          </div>
        )}

        {/* --- VIEW 4: LOGIN PAGE --- */}
        {currentView === 'login' && (
          <div className="auth-container animate-fade-in">
            <div className="auth-card glass-panel">
              <div className="auth-header">
                <Lock size={32} style={{ color: 'var(--accent-color)', marginBottom: '12px' }} />
                <h2 className="auth-title">Sign In</h2>
                <p className="auth-subtitle">Access your event registrations and tickets.</p>
              </div>

              <form onSubmit={handleLogin}>
                <div className="form-group">
                  <label className="form-label">Email Address</label>
                  <div style={{ position: 'relative' }}>
                    <Mail size={16} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                    <input 
                      type="email" 
                      className="form-input" 
                      style={{ paddingLeft: '42px' }}
                      placeholder="user@ticket-hub.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required 
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Password</label>
                  <div style={{ position: 'relative' }}>
                    <Lock size={16} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                    <input 
                      type="password" 
                      className="form-input" 
                      style={{ paddingLeft: '42px' }}
                      placeholder="••••••••"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required 
                    />
                  </div>
                </div>

                <button 
                  type="submit" 
                  className="btn btn-primary" 
                  style={{ width: '100%', marginTop: '8px' }}
                  disabled={loading}
                >
                  {loading ? <Loader size={18} className="spinner" /> : "Sign In"}
                </button>
              </form>

              <div style={{ marginTop: '24px', fontSize: '0.88rem', color: 'var(--text-secondary)' }}>
                Don't have an account?{' '}
                <span 
                  style={{ color: 'var(--accent-color)', fontWeight: 600, cursor: 'pointer' }}
                  onClick={() => setCurrentView('register')}
                >
                  Register Here
                </span>
              </div>
              
              <div style={{ marginTop: '20px', padding: '12px', background: 'rgba(255,255,255,0.02)', borderRadius: '6px', fontSize: '0.8rem', border: '1px solid var(--border-color)', textAlign: 'left' }}>
                <span style={{ fontWeight: 700, color: 'var(--accent-color)' }}>Quick Demo Logins:</span>
                <div style={{ marginTop: '4px' }}>• Admin: <code>admin@ticket-hub.com</code> / <code>Password123</code></div>
                <div>• Attendee: <code>user@ticket-hub.com</code> / <code>Password123</code></div>
              </div>
            </div>
          </div>
        )}

        {/* --- VIEW 5: REGISTER PAGE --- */}
        {currentView === 'register' && (
          <div className="auth-container animate-fade-in">
            <div className="auth-card glass-panel">
              <div className="auth-header">
                <User size={32} style={{ color: 'var(--accent-color)', marginBottom: '12px' }} />
                <h2 className="auth-title">Create Account</h2>
                <p className="auth-subtitle">Join us to register for local and global events.</p>
              </div>

              <form onSubmit={handleRegisterUser}>
                <div className="form-group">
                  <label className="form-label">Full Name</label>
                  <div style={{ position: 'relative' }}>
                    <User size={16} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                    <input 
                      type="text" 
                      className="form-input" 
                      style={{ paddingLeft: '42px' }}
                      placeholder="Jane Doe"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      required 
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Email Address</label>
                  <div style={{ position: 'relative' }}>
                    <Mail size={16} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                    <input 
                      type="email" 
                      className="form-input" 
                      style={{ paddingLeft: '42px' }}
                      placeholder="jane.doe@example.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required 
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Password</label>
                  <div style={{ position: 'relative' }}>
                    <Lock size={16} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                    <input 
                      type="password" 
                      className="form-input" 
                      style={{ paddingLeft: '42px' }}
                      placeholder="Min. 8 characters"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required 
                    />
                  </div>
                </div>

                <button 
                  type="submit" 
                  className="btn btn-primary" 
                  style={{ width: '100%', marginTop: '8px' }}
                  disabled={loading}
                >
                  {loading ? <Loader size={18} className="spinner" /> : "Sign Up"}
                </button>
              </form>

              <div style={{ marginTop: '24px', fontSize: '0.88rem', color: 'var(--text-secondary)' }}>
                Already have an account?{' '}
                <span 
                  style={{ color: 'var(--accent-color)', fontWeight: 600, cursor: 'pointer' }}
                  onClick={() => setCurrentView('login')}
                >
                  Sign In
                </span>
              </div>
            </div>
          </div>
        )}

        {/* --- VIEW 6: ADMIN EVENTS MANAGEMENT --- */}
        {currentView === 'admin-events' && user?.is_admin && (
          <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            <div className="admin-header">
              <div style={{ textAlign: 'left' }}>
                <h1 style={{ fontSize: '2rem', marginBottom: '8px' }}>Admin Dashboard</h1>
                <p style={{ color: 'var(--text-secondary)' }}>Create, edit, and delete ticketing events on this platform.</p>
              </div>

              <button 
                className="btn btn-primary"
                onClick={() => {
                  setEditEventId(null);
                  setEventTitle('');
                  setEventDescription('');
                  setEventLocation('');
                  setEventStartsAt('');
                  setEventEndsAt('');
                  setEventCapacity(100);
                  setEventPrice('0.00');
                  setEventIsPublished(true);
                  setCurrentView('admin-form');
                }}
              >
                <Plus size={16} />
                <span>Create New Event</span>
              </button>
            </div>

            <div className="admin-table-card glass-panel">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Event details</th>
                    <th>Date & time</th>
                    <th>Admission fee</th>
                    <th>Bookings</th>
                    <th>Status</th>
                    <th style={{ textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {adminEvents.map((evt) => (
                    <tr key={evt.id}>
                      <td>
                        <div style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{evt.title}</div>
                        <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '4px', marginTop: '2px' }}>
                          <MapPin size={12} />
                          {evt.location || "N/A"}
                        </div>
                      </td>
                      <td style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                        {formatDate(evt.starts_at)}
                      </td>
                      <td>
                        <span style={{ fontWeight: 600 }}>
                          {parseFloat(evt.price) === 0 ? "Free" : `$${parseFloat(evt.price).toFixed(2)}`}
                        </span>
                      </td>
                      <td style={{ fontSize: '0.85rem' }}>
                        <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
                          {evt.capacity - evt.spots_remaining}
                        </span>
                        <span style={{ color: 'var(--text-muted)' }}> / {evt.capacity}</span>
                      </td>
                      <td>
                        <span className={`badge ${evt.is_published ? 'badge-success' : 'badge-warning'}`}>
                          {evt.is_published ? "Published" : "Draft"}
                        </span>
                      </td>
                      <td>
                        <div className="admin-actions" style={{ justifyContent: 'flex-end' }}>
                          <button className="btn btn-secondary" style={{ padding: '8px 12px' }} onClick={() => handleEditClick(evt)}>
                            <Edit size={14} />
                          </button>
                          <button className="btn btn-danger" style={{ padding: '8px 12px' }} onClick={() => handleDeleteEvent(evt.id)}>
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* --- VIEW 7: ADMIN FORM (CREATE / EDIT) --- */}
        {currentView === 'admin-form' && user?.is_admin && (
          <div className="animate-fade-in">
            <button 
              className="btn btn-secondary" 
              style={{ marginBottom: '24px' }}
              onClick={() => setCurrentView('admin-events')}
            >
              <ArrowLeft size={16} />
              <span>Cancel & Return</span>
            </button>

            <div className="admin-form-card glass-panel">
              <h2 style={{ fontSize: '1.5rem', marginBottom: '24px', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
                {editEventId ? "Modify Event Details" : "Publish New Event"}
              </h2>

              <form onSubmit={handleCreateOrUpdateEvent}>
                <div className="form-group">
                  <label className="form-label">Event Title *</label>
                  <input 
                    type="text" 
                    className="form-input" 
                    placeholder="e.g. Symphony Concert"
                    value={eventTitle}
                    onChange={(e) => setEventTitle(e.target.value)}
                    required 
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Event Description</label>
                  <textarea 
                    className="form-input" 
                    rows={4}
                    style={{ resize: 'vertical' }}
                    placeholder="Write details or details about this event..."
                    value={eventDescription}
                    onChange={(e) => setEventDescription(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Location / Venue</label>
                  <div style={{ position: 'relative' }}>
                    <MapPin size={16} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                    <input 
                      type="text" 
                      className="form-input" 
                      style={{ paddingLeft: '42px' }}
                      placeholder="e.g. Austin City Hall or Zoom Virtual"
                      value={eventLocation}
                      onChange={(e) => setEventLocation(e.target.value)}
                    />
                  </div>
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Starts At *</label>
                    <input 
                      type="datetime-local" 
                      className="form-input" 
                      value={eventStartsAt}
                      onChange={(e) => setEventStartsAt(e.target.value)}
                      required 
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Ends At *</label>
                    <input 
                      type="datetime-local" 
                      className="form-input" 
                      value={eventEndsAt}
                      onChange={(e) => setEventEndsAt(e.target.value)}
                      required 
                    />
                  </div>
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Total Seating Capacity *</label>
                    <input 
                      type="number" 
                      min="1"
                      className="form-input" 
                      value={eventCapacity}
                      onChange={(e) => setEventCapacity(parseInt(e.target.value) || 0)}
                      required 
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Price ($ USD) *</label>
                    <input 
                      type="number" 
                      step="0.01"
                      min="0"
                      className="form-input" 
                      placeholder="0.00"
                      value={eventPrice}
                      onChange={(e) => setEventPrice(e.target.value)}
                      required 
                    />
                  </div>
                </div>

                <div className="form-group" style={{ margin: '8px 0 24px' }}>
                  <label className="form-checkbox-container">
                    <input 
                      type="checkbox" 
                      className="form-checkbox" 
                      checked={eventIsPublished}
                      onChange={(e) => setEventIsPublished(e.target.checked)}
                    />
                    <span style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                      Publish Immediately (makes visible on public listings)
                    </span>
                  </label>
                </div>

                <button 
                  type="submit" 
                  className="btn btn-primary" 
                  style={{ width: '100%', padding: '14px' }}
                  disabled={loading}
                >
                  {loading ? <Loader size={18} className="spinner" /> : (editEventId ? "Save Modifications" : "Deploy Event")}
                </button>
              </form>
            </div>
          </div>
        )}

        {/* --- VIEW 8: ADMIN TICKET VALIDATOR SCANNER --- */}
        {currentView === 'admin-validate' && user?.is_admin && (
          <div className="animate-fade-in">
            <div className="validation-card glass-panel">
              <ShieldCheck size={36} style={{ color: 'var(--accent-color)', marginBottom: '12px' }} />
              <h2 style={{ fontSize: '1.5rem', marginBottom: '8px' }}>Gate Check-In / Ticket Validator</h2>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                Enter the unique Ticket Reference Code or ID below to validate the attendee's entry ticket.
              </p>

              <form onSubmit={handleValidateTicket}>
                <div className="validation-input-group">
                  <input 
                    type="text" 
                    className="form-input" 
                    placeholder="Enter full Ticket Code or ID..."
                    value={validateCode}
                    onChange={(e) => setValidateCode(e.target.value)}
                    required
                  />
                  <button type="submit" className="btn btn-primary" disabled={loading}>
                    {loading ? <Loader size={16} className="spinner" /> : "Validate"}
                  </button>
                </div>
              </form>

              {validationResult && (
                <div className={`result-box ${validationResult.valid ? 'result-box-success' : 'result-box-error'}`}>
                  <div className={`result-icon ${validationResult.valid ? 'result-icon-success' : 'result-icon-error'}`}>
                    {validationResult.valid ? <Check size={24} /> : <XCircle size={24} />}
                  </div>
                  
                  <h3 className="result-title" style={{ color: validationResult.valid ? 'var(--success)' : 'var(--error)' }}>
                    {validationResult.valid ? "Access Granted" : "Access Denied"}
                  </h3>
                  <p className="result-msg">{validationResult.message}</p>
                  
                  {validationResult.ticket && (
                    <div className="result-details">
                      <div>
                        <strong>Attendee:</strong> {validationResult.ticket.registration_id ? "Authenticated System Guest" : "Unknown"}
                      </div>
                      <div>
                        <strong>Event Title:</strong> {validationResult.ticket.event?.title || "N/A"}
                      </div>
                      <div>
                        <strong>Venue:</strong> {validationResult.ticket.event?.location || "N/A"}
                      </div>
                      <div>
                        <strong>Checked-In At:</strong> {validationResult.ticket.used_at ? formatDate(validationResult.ticket.used_at) : "Just Now"}
                      </div>
                      <div style={{ wordBreak: 'break-all', fontSize: '0.75rem', marginTop: '4px', fontFamily: 'var(--mono-font)' }}>
                        <strong>Reference:</strong> {validationResult.ticket.id}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

      </main>

      {/* Footer */}
      <footer style={{ marginTop: 'auto', padding: '32px 20px', borderTop: '1px solid var(--border-color)', color: 'var(--text-muted)', fontSize: '0.8rem', textAlign: 'center' }}>
        <div>&copy; 2026 Team Alpha, Azubi Africa. All rights reserved. Built on AWS ECS, RDS, and S3.</div>
        <div style={{ marginTop: '6px' }}>Version 1.0.0 (Local SQLite Mode)</div>
      </footer>
    </>
  );
}

export default App;
