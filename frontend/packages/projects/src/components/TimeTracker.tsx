import React, { useState, useEffect } from 'react';
import { Button, Input, Card } from '@dotmac/primitives';
import {
  Play,
  Pause,
  Square,
  Clock,
  Plus,
  Edit,
  Trash2,
  Calendar,
  Timer,
  TrendingUp
} from 'lucide-react';
import { format, formatDistanceToNow, startOfWeek, endOfWeek } from 'date-fns';
import { useTimeTracking } from '../hooks';
import type { TimeTrackerProps, TimeEntry } from '../types';

export const TimeTracker: React.FC<TimeTrackerProps> = ({
  projectId,
  taskId,
  showHistory = true,
  allowBulkEntry = true
}) => {
  const {
    timeEntries,
    loading,
    error,
    currentEntry,
    startTimer,
    stopTimer,
    createTimeEntry,
    updateTimeEntry,
    deleteTimeEntry,
    isTimerRunning,
    currentDuration,
    refreshTimeEntries
  } = useTimeTracking();

  const [timerDescription, setTimerDescription] = useState('Working on project');
  const [showManualEntry, setShowManualEntry] = useState(false);
  const [editingEntry, setEditingEntry] = useState<TimeEntry | null>(null);
  const [manualEntry, setManualEntry] = useState({
    description: '',
    start_time: '',
    end_time: '',
    activity_type: 'development' as const,
    billable: true
  });

  // Format duration from seconds to HH:MM:SS
  const formatDuration = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  // Format duration from minutes to readable format
  const formatMinutes = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;

    if (hours > 0) {
      return `${hours}h ${mins}m`;
    }
    return `${mins}m`;
  };

  const handleStartTimer = async () => {
    if (!projectId) return;

    try {
      await startTimer(projectId, taskId, timerDescription);
    } catch (err) {
      console.error('Failed to start timer:', err);
    }
  };

  const handleStopTimer = async () => {
    try {
      await stopTimer();
      setTimerDescription('Working on project');
    } catch (err) {
      console.error('Failed to stop timer:', err);
    }
  };

  const handleManualEntry = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!projectId || !manualEntry.description.trim() || !manualEntry.start_time || !manualEntry.end_time) {
      return;
    }

    try {
      await createTimeEntry({
        project_id: projectId,
        task_id: taskId,
        ...manualEntry
      });

      // Reset form
      setManualEntry({
        description: '',
        start_time: '',
        end_time: '',
        activity_type: 'development',
        billable: true
      });
      setShowManualEntry(false);
    } catch (err) {
      console.error('Failed to create time entry:', err);
    }
  };

  const handleEditEntry = async (entry: TimeEntry, updates: Partial<TimeEntry>) => {
    try {
      await updateTimeEntry(entry.id, {
        description: updates.description || entry.description,
        start_time: updates.start_time || entry.start_time,
        end_time: updates.end_time || entry.end_time,
        activity_type: updates.activity_type || entry.activity_type,
        billable: updates.billable !== undefined ? updates.billable : entry.billable
      });
      setEditingEntry(null);
    } catch (err) {
      console.error('Failed to update time entry:', err);
    }
  };

  const handleDeleteEntry = async (entryId: string) => {
    if (!confirm('Are you sure you want to delete this time entry?')) return;

    try {
      await deleteTimeEntry(entryId);
    } catch (err) {
      console.error('Failed to delete time entry:', err);
    }
  };

  // Calculate totals
  const filteredEntries = timeEntries.filter(entry =>
    (!projectId || entry.project_id === projectId) &&
    (!taskId || entry.task_id === taskId)
  );

  const todayEntries = filteredEntries.filter(entry =>
    format(new Date(entry.start_time), 'yyyy-MM-dd') === format(new Date(), 'yyyy-MM-dd')
  );

  const weekEntries = filteredEntries.filter(entry => {
    const entryDate = new Date(entry.start_time);
    const weekStart = startOfWeek(new Date(), { weekStartsOn: 1 });
    const weekEnd = endOfWeek(new Date(), { weekStartsOn: 1 });
    return entryDate >= weekStart && entryDate <= weekEnd;
  });

  const todayTotal = todayEntries.reduce((sum, entry) => sum + entry.duration_minutes, 0);
  const weekTotal = weekEntries.reduce((sum, entry) => sum + entry.duration_minutes, 0);
  const billableToday = todayEntries.filter(e => e.billable).reduce((sum, entry) => sum + entry.duration_minutes, 0);

  if (error) {
    return (
      <Card className="border-red-200 bg-red-50 p-4">
        <div className="text-red-800">
          <h3 className="font-semibold">Time Tracking Error</h3>
          <p>{error}</p>
        </div>
      </Card>
    );
  }

  return (
    <div className="time-tracker space-y-6">
      {/* Timer Section */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold flex items-center gap-2">
            <Timer className="h-5 w-5" />
            Time Tracker
          </h2>

          <div className="flex items-center gap-4 text-sm text-gray-600">
            <div className="flex items-center gap-1">
              <Clock className="h-4 w-4" />
              <span>Today: {formatMinutes(todayTotal)}</span>
            </div>
            <div className="flex items-center gap-1">
              <Calendar className="h-4 w-4" />
              <span>Week: {formatMinutes(weekTotal)}</span>
            </div>
            <div className="flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              <span>Billable: {formatMinutes(billableToday)}</span>
            </div>
          </div>
        </div>

        {/* Current Timer */}
        <div className="bg-gray-50 rounded-lg p-4 mb-4">
          <div className="flex items-center justify-between">
            <div className="flex-1">
              {isTimerRunning ? (
                <div>
                  <div className="text-2xl font-mono font-bold text-green-600 mb-2">
                    {formatDuration(currentDuration)}
                  </div>
                  <p className="text-sm text-gray-600">
                    {currentEntry?.description || 'Timer running...'}
                  </p>
                </div>
              ) : (
                <div>
                  <Input
                    placeholder="What are you working on?"
                    value={timerDescription}
                    onChange={(e) => setTimerDescription(e.target.value)}
                    className="mb-2"
                  />
                  <p className="text-sm text-gray-500">Ready to start tracking time</p>
                </div>
              )}
            </div>

            <div className="flex items-center gap-2">
              {isTimerRunning ? (
                <Button
                  onClick={handleStopTimer}
                  className="bg-red-600 hover:bg-red-700"
                >
                  <Square className="h-4 w-4" />
                  Stop
                </Button>
              ) : (
                <Button
                  onClick={handleStartTimer}
                  disabled={!projectId || !timerDescription.trim()}
                  className="bg-green-600 hover:bg-green-700"
                >
                  <Play className="h-4 w-4" />
                  Start
                </Button>
              )}
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowManualEntry(!showManualEntry)}
          >
            <Plus className="h-4 w-4" />
            Manual Entry
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={refreshTimeEntries}
          >
            Refresh
          </Button>
        </div>
      </Card>

      {/* Manual Entry Form */}
      {showManualEntry && (
        <Card className="p-4">
          <h3 className="font-semibold mb-4">Add Time Entry</h3>

          <form onSubmit={handleManualEntry} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Description</label>
              <Input
                required
                placeholder="What did you work on?"
                value={manualEntry.description}
                onChange={(e) => setManualEntry(prev => ({ ...prev, description: e.target.value }))}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Start Time</label>
                <Input
                  type="datetime-local"
                  required
                  value={manualEntry.start_time}
                  onChange={(e) => setManualEntry(prev => ({ ...prev, start_time: e.target.value }))}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">End Time</label>
                <Input
                  type="datetime-local"
                  required
                  value={manualEntry.end_time}
                  onChange={(e) => setManualEntry(prev => ({ ...prev, end_time: e.target.value }))}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Activity Type</label>
                <select
                  value={manualEntry.activity_type}
                  onChange={(e) => setManualEntry(prev => ({ ...prev, activity_type: e.target.value as any }))}
                  className="w-full p-2 border border-gray-300 rounded-md"
                >
                  <option value="development">Development</option>
                  <option value="meeting">Meeting</option>
                  <option value="documentation">Documentation</option>
                  <option value="testing">Testing</option>
                  <option value="review">Review</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div>
                <label className="flex items-center mt-6">
                  <input
                    type="checkbox"
                    checked={manualEntry.billable}
                    onChange={(e) => setManualEntry(prev => ({ ...prev, billable: e.target.checked }))}
                    className="mr-2"
                  />
                  Billable
                </label>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button type="submit">
                Add Entry
              </Button>

              <Button
                type="button"
                variant="outline"
                onClick={() => setShowManualEntry(false)}
              >
                Cancel
              </Button>
            </div>
          </form>
        </Card>
      )}

      {/* Time Entries History */}
      {showHistory && (
        <Card className="p-4">
          <h3 className="font-semibold mb-4">Recent Time Entries</h3>

          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3].map(i => (
                <div key={i} className="animate-pulse flex items-center gap-3 p-3 border rounded-lg">
                  <div className="h-4 bg-gray-200 rounded w-1/4"></div>
                  <div className="h-4 bg-gray-200 rounded w-1/2"></div>
                  <div className="h-4 bg-gray-200 rounded w-1/4"></div>
                </div>
              ))}
            </div>
          ) : filteredEntries.length > 0 ? (
            <div className="space-y-2">
              {filteredEntries
                .sort((a, b) => new Date(b.start_time).getTime() - new Date(a.start_time).getTime())
                .slice(0, 10)
                .map((entry) => (
                  <div
                    key={entry.id}
                    className="flex items-center justify-between p-3 border border-gray-100 rounded-lg hover:bg-gray-50"
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h4 className="font-medium text-sm">{entry.description}</h4>
                        {entry.billable && (
                          <span className="px-1.5 py-0.5 text-xs bg-green-100 text-green-700 rounded">
                            Billable
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-4 text-xs text-gray-500">
                        <span>{format(new Date(entry.start_time), 'MMM dd, HH:mm')}</span>
                        <span>•</span>
                        <span>{entry.activity_type}</span>
                        <span>•</span>
                        <span>{entry.user_name}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <div className="text-right">
                        <div className="font-medium text-sm">
                          {formatMinutes(entry.duration_minutes)}
                        </div>
                        {entry.hourly_rate && (
                          <div className="text-xs text-gray-500">
                            ${(entry.hourly_rate * entry.duration_minutes / 60).toFixed(2)}
                          </div>
                        )}
                      </div>

                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setEditingEntry(entry)}
                        >
                          <Edit className="h-3 w-3" />
                        </Button>

                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeleteEntry(entry.id)}
                          className="text-red-600 hover:text-red-700"
                        >
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              <Clock className="h-8 w-8 mx-auto mb-3 opacity-50" />
              <p>No time entries found</p>
              <p className="text-sm">Start the timer or add a manual entry to begin tracking time</p>
            </div>
          )}
        </Card>
      )}
    </div>
  );
};
