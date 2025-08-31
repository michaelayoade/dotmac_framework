/**
 * Visual Workflow Designer
 * Drag-and-drop workflow designer using existing WorkflowTemplate infrastructure
 */

import React, { useState, useCallback, useMemo } from 'react';
import { clsx } from 'clsx';
import {
  DragDropContext,
  Droppable,
  Draggable,
  DropResult,
} from '@hello-pangea/dnd';
import { Card, Button, Input, Select, Textarea, Badge } from '@dotmac/primitives';
import { PermissionGuard } from '@dotmac/rbac';
import { withComponentRegistration } from '@dotmac/registry';
import { useRenderProfiler } from '@dotmac/primitives/utils/performance';
import { standard_exception_handler } from '@dotmac/shared';
import {
  WorkflowDefinition,
  WorkflowStepConfig,
  WorkflowConfig
} from '../types';
import { WorkflowTemplate } from '@dotmac/patterns';
import {
  Plus,
  Trash2,
  Edit3,
  Play,
  Save,
  Settings,
  GitBranch,
  ArrowRight,
  Zap,
  FileText,
  Users,
  Check,
  AlertCircle
} from 'lucide-react';

// Step types available in the designer
const STEP_TYPES = {
  form: {
    label: 'Form Step',
    icon: FileText,
    color: 'bg-blue-100 text-blue-800',
    defaultFields: [
      { key: 'input', label: 'User Input', type: 'text', required: true }
    ]
  },
  approval: {
    label: 'Approval Step',
    icon: Check,
    color: 'bg-green-100 text-green-800',
    defaultFields: [
      { key: 'approver', label: 'Approver', type: 'select', required: true }
    ]
  },
  action: {
    label: 'Action Step',
    icon: Zap,
    color: 'bg-orange-100 text-orange-800',
    defaultFields: [
      { key: 'action_type', label: 'Action Type', type: 'select', required: true }
    ]
  },
  conditional: {
    label: 'Conditional Step',
    icon: GitBranch,
    color: 'bg-purple-100 text-purple-800',
    defaultFields: []
  },
  review: {
    label: 'Review Step',
    icon: Users,
    color: 'bg-yellow-100 text-yellow-800',
    defaultFields: [
      { key: 'reviewer', label: 'Reviewer', type: 'select', required: true }
    ]
  }
};

interface VisualWorkflowDesignerProps {
  initialDefinition?: WorkflowDefinition;
  onSave?: (definition: WorkflowDefinition) => Promise<void>;
  onTest?: (definition: WorkflowDefinition) => Promise<void>;
  readOnly?: boolean;
  className?: string;
}

interface DesignerStep extends WorkflowStepConfig {
  tempId?: string;
  position: { x: number; y: number };
}

function VisualWorkflowDesignerImpl({
  initialDefinition,
  onSave,
  onTest,
  readOnly = false,
  className = ''
}: VisualWorkflowDesignerProps) {
  useRenderProfiler('VisualWorkflowDesigner', { 
    stepsCount: initialDefinition?.steps?.length || 0 
  });

  // State
  const [definition, setDefinition] = useState<WorkflowDefinition>({
    id: '',
    name: 'New Workflow',
    description: '',
    version: '1.0.0',
    steps: [],
    settings: {
      autoStart: false,
      allowStepNavigation: true,
      showProgress: true,
      persistData: true
    },
    ...initialDefinition
  });
  
  const [selectedStep, setSelectedStep] = useState<string | null>(null);
  const [editingStep, setEditingStep] = useState<DesignerStep | null>(null);
  const [previewMode, setPreviewMode] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // Convert steps to designer format with positions
  const designerSteps = useMemo((): DesignerStep[] => {
    return definition.steps.map((step, index) => ({
      ...step,
      position: { x: 50 + (index * 200), y: 100 }
    }));
  }, [definition.steps]);

  // Step operations
  const addStep = useCallback((stepType: keyof typeof STEP_TYPES) => {
    const stepConfig = STEP_TYPES[stepType];
    const newStep: DesignerStep = {
      id: `step_${Date.now()}`,
      tempId: `temp_${Date.now()}`,
      name: stepConfig.label,
      type: stepType,
      title: stepConfig.label,
      description: `New ${stepConfig.label}`,
      fields: stepConfig.defaultFields.map(field => ({
        ...field,
        id: `field_${Date.now()}_${field.key}`
      })),
      actions: [],
      required: true,
      position: { x: 50 + (designerSteps.length * 200), y: 100 }
    };

    setDefinition(prev => ({
      ...prev,
      steps: [...prev.steps, newStep]
    }));
    
    setSelectedStep(newStep.id);
  }, [designerSteps.length]);

  const updateStep = useCallback((stepId: string, updates: Partial<WorkflowStepConfig>) => {
    setDefinition(prev => ({
      ...prev,
      steps: prev.steps.map(step => 
        step.id === stepId ? { ...step, ...updates } : step
      )
    }));
  }, []);

  const deleteStep = useCallback((stepId: string) => {
    setDefinition(prev => ({
      ...prev,
      steps: prev.steps.filter(step => step.id !== stepId)
    }));
    
    if (selectedStep === stepId) {
      setSelectedStep(null);
    }
  }, [selectedStep]);

  const reorderSteps = useCallback((result: DropResult) => {
    if (!result.destination) return;

    const items = Array.from(definition.steps);
    const [reorderedItem] = items.splice(result.source.index, 1);
    items.splice(result.destination.index, 0, reorderedItem);

    setDefinition(prev => ({ ...prev, steps: items }));
  }, [definition.steps]);

  // Save workflow
  const handleSave = useCallback(async () => {
    if (readOnly || !onSave) return;
    
    setIsSaving(true);
    try {
      await onSave(definition);
    } catch (error) {
      console.error('Failed to save workflow:', error);
    } finally {
      setIsSaving(false);
    }
  }, [definition, onSave, readOnly]);

  // Test workflow
  const handleTest = useCallback(async () => {
    if (!onTest) return;
    
    try {
      await onTest(definition);
    } catch (error) {
      console.error('Failed to test workflow:', error);
    }
  }, [definition, onTest]);

  // Convert to WorkflowConfig for preview
  const previewConfig = useMemo((): WorkflowConfig => ({
    title: definition.name,
    description: definition.description,
    steps: definition.steps,
    showProgress: definition.settings.showProgress,
    allowStepNavigation: definition.settings.allowStepNavigation,
    persistData: definition.settings.persistData,
    autoSave: definition.settings.persistData,
    autoSaveInterval: 30000
  }), [definition]);

  if (previewMode) {
    return (
      <div className="h-full flex flex-col">
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-semibold">Workflow Preview</h2>
          <Button 
            variant="outline" 
            onClick={() => setPreviewMode(false)}
          >
            Back to Designer
          </Button>
        </div>
        <div className="flex-1 p-6">
          <WorkflowTemplate
            config={previewConfig}
            onComplete={async (data) => {
              console.log('Preview completed:', data);
            }}
          />
        </div>
      </div>
    );
  }

  return (
    <div className={clsx('h-full flex', className)}>
      {/* Toolbar */}
      <div className="w-64 border-r bg-gray-50 flex flex-col">
        <div className="p-4 border-b">
          <h3 className="font-medium text-gray-900">Workflow Steps</h3>
        </div>
        
        <div className="flex-1 p-4 space-y-2">
          {Object.entries(STEP_TYPES).map(([type, config]) => {
            const Icon = config.icon;
            return (
              <button
                key={type}
                onClick={() => addStep(type as keyof typeof STEP_TYPES)}
                disabled={readOnly}
                className={clsx(
                  'w-full flex items-center space-x-3 p-3 rounded-lg border-2 border-dashed',
                  'transition-colors hover:bg-white hover:border-gray-300',
                  readOnly && 'opacity-50 cursor-not-allowed'
                )}
              >
                <div className={clsx('p-2 rounded', config.color)}>
                  <Icon className="h-4 w-4" />
                </div>
                <span className="text-sm font-medium">{config.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Designer Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center space-x-4">
            <div>
              <Input
                value={definition.name}
                onChange={(e) => setDefinition(prev => ({ ...prev, name: e.target.value }))}
                placeholder="Workflow Name"
                className="text-lg font-semibold"
                disabled={readOnly}
              />
              <Input
                value={definition.description}
                onChange={(e) => setDefinition(prev => ({ ...prev, description: e.target.value }))}
                placeholder="Workflow Description"
                className="text-sm text-gray-600 mt-1"
                disabled={readOnly}
              />
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              onClick={() => setPreviewMode(true)}
              className="flex items-center space-x-2"
            >
              <Play className="h-4 w-4" />
              <span>Preview</span>
            </Button>
            
            {onTest && (
              <Button
                variant="outline"
                onClick={handleTest}
                className="flex items-center space-x-2"
              >
                <AlertCircle className="h-4 w-4" />
                <span>Test</span>
              </Button>
            )}
            
            {!readOnly && onSave && (
              <Button
                onClick={handleSave}
                disabled={isSaving}
                className="flex items-center space-x-2"
              >
                <Save className={clsx('h-4 w-4', isSaving && 'animate-spin')} />
                <span>{isSaving ? 'Saving...' : 'Save'}</span>
              </Button>
            )}
          </div>
        </div>

        {/* Canvas */}
        <div className="flex-1 relative bg-gray-50 overflow-auto">
          <DragDropContext onDragEnd={reorderSteps}>
            <Droppable droppableId="workflow-canvas">
              {(provided) => (
                <div 
                  ref={provided.innerRef}
                  {...provided.droppableProps}
                  className="min-h-full p-6"
                >
                  {designerSteps.map((step, index) => (
                    <Draggable 
                      key={step.id} 
                      draggableId={step.id} 
                      index={index}
                      isDragDisabled={readOnly}
                    >
                      {(provided, snapshot) => (
                        <div
                          ref={provided.innerRef}
                          {...provided.draggableProps}
                          {...provided.dragHandleProps}
                          className={clsx(
                            'mb-4 transition-all',
                            snapshot.isDragging && 'rotate-3 scale-105'
                          )}
                        >
                          <StepCard
                            step={step}
                            index={index}
                            isSelected={selectedStep === step.id}
                            readOnly={readOnly}
                            onSelect={() => setSelectedStep(step.id)}
                            onEdit={() => setEditingStep(step)}
                            onDelete={() => deleteStep(step.id)}
                            onUpdate={(updates) => updateStep(step.id, updates)}
                          />
                          
                          {/* Connection Arrow */}
                          {index < designerSteps.length - 1 && (
                            <div className="flex justify-center my-2">
                              <ArrowRight className="h-6 w-6 text-gray-400" />
                            </div>
                          )}
                        </div>
                      )}
                    </Draggable>
                  ))}
                  {provided.placeholder}
                  
                  {designerSteps.length === 0 && (
                    <div className="flex items-center justify-center h-64 text-gray-500">
                      <div className="text-center">
                        <FileText className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                        <p className="text-lg font-medium">No steps added yet</p>
                        <p className="text-sm">Drag steps from the toolbar to build your workflow</p>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </Droppable>
          </DragDropContext>
        </div>
      </div>

      {/* Properties Panel */}
      {(selectedStep || editingStep) && (
        <div className="w-80 border-l bg-white flex flex-col">
          <StepPropertiesPanel
            step={editingStep || designerSteps.find(s => s.id === selectedStep)}
            readOnly={readOnly}
            onUpdate={(updates) => {
              const stepId = editingStep?.id || selectedStep;
              if (stepId) updateStep(stepId, updates);
            }}
            onClose={() => {
              setEditingStep(null);
              setSelectedStep(null);
            }}
          />
        </div>
      )}
    </div>
  );
}

// Step Card Component
interface StepCardProps {
  step: DesignerStep;
  index: number;
  isSelected: boolean;
  readOnly: boolean;
  onSelect: () => void;
  onEdit: () => void;
  onDelete: () => void;
  onUpdate: (updates: Partial<WorkflowStepConfig>) => void;
}

function StepCard({ 
  step, 
  index, 
  isSelected, 
  readOnly,
  onSelect, 
  onEdit, 
  onDelete,
  onUpdate 
}: StepCardProps) {
  const stepConfig = STEP_TYPES[step.type as keyof typeof STEP_TYPES];
  const Icon = stepConfig?.icon || FileText;

  return (
    <Card 
      className={clsx(
        'cursor-pointer transition-all',
        isSelected && 'ring-2 ring-blue-500 ring-offset-2',
        'hover:shadow-md'
      )}
      onClick={onSelect}
    >
      <div className="p-4">
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-3">
            <div className={clsx('p-2 rounded', stepConfig?.color || 'bg-gray-100')}>
              <Icon className="h-4 w-4" />
            </div>
            
            <div className="flex-1">
              <div className="flex items-center space-x-2">
                <Badge variant="secondary">{index + 1}</Badge>
                <h4 className="font-medium">{step.title}</h4>
                {step.required && (
                  <Badge variant="destructive" className="text-xs">Required</Badge>
                )}
              </div>
              
              {step.description && (
                <p className="text-sm text-gray-600 mt-1">{step.description}</p>
              )}
              
              <div className="flex items-center space-x-2 mt-2 text-xs text-gray-500">
                <span>Fields: {step.fields.length}</span>
                <span>•</span>
                <span>Actions: {step.actions.length}</span>
              </div>
            </div>
          </div>
          
          {!readOnly && (
            <div className="flex items-center space-x-1">
              <Button
                size="sm"
                variant="ghost"
                onClick={(e) => {
                  e.stopPropagation();
                  onEdit();
                }}
              >
                <Edit3 className="h-4 w-4" />
              </Button>
              
              <Button
                size="sm"
                variant="ghost"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete();
                }}
                className="text-red-600 hover:text-red-800"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}

// Step Properties Panel
interface StepPropertiesPanelProps {
  step: DesignerStep | undefined;
  readOnly: boolean;
  onUpdate: (updates: Partial<WorkflowStepConfig>) => void;
  onClose: () => void;
}

function StepPropertiesPanel({ step, readOnly, onUpdate, onClose }: StepPropertiesPanelProps) {
  if (!step) return null;

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between p-4 border-b">
        <h3 className="font-medium">Step Properties</h3>
        <Button size="sm" variant="ghost" onClick={onClose}>
          ×
        </Button>
      </div>
      
      <div className="flex-1 p-4 space-y-4 overflow-auto">
        {/* Basic Properties */}
        <div>
          <label className="block text-sm font-medium mb-2">Step Name</label>
          <Input
            value={step.title}
            onChange={(e) => onUpdate({ title: e.target.value })}
            disabled={readOnly}
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium mb-2">Description</label>
          <Textarea
            value={step.description || ''}
            onChange={(e) => onUpdate({ description: e.target.value })}
            disabled={readOnly}
            rows={3}
          />
        </div>
        
        <div className="flex items-center space-x-3">
          <input
            type="checkbox"
            id="required"
            checked={step.required}
            onChange={(e) => onUpdate({ required: e.target.checked })}
            disabled={readOnly}
          />
          <label htmlFor="required" className="text-sm font-medium">Required Step</label>
        </div>
        
        <div className="flex items-center space-x-3">
          <input
            type="checkbox"
            id="skippable"
            checked={step.skippable || false}
            onChange={(e) => onUpdate({ skippable: e.target.checked })}
            disabled={readOnly}
          />
          <label htmlFor="skippable" className="text-sm font-medium">Allow Skip</label>
        </div>

        {/* Fields Section */}
        <div>
          <h4 className="font-medium mb-2">Form Fields</h4>
          <div className="space-y-2">
            {step.fields.map((field, index) => (
              <div key={field.id || index} className="p-3 bg-gray-50 rounded">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium">{field.label}</span>
                  <Badge variant="outline" className="text-xs">{field.type}</Badge>
                </div>
                <p className="text-xs text-gray-600">Key: {field.key}</p>
              </div>
            ))}
            
            {!readOnly && (
              <Button
                size="sm"
                variant="outline"
                className="w-full"
                onClick={() => {
                  const newField = {
                    id: `field_${Date.now()}`,
                    key: `field_${step.fields.length + 1}`,
                    label: 'New Field',
                    type: 'text' as const,
                    required: false
                  };
                  onUpdate({ 
                    fields: [...step.fields, newField] 
                  });
                }}
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Field
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export const VisualWorkflowDesigner = standard_exception_handler(
  withComponentRegistration(VisualWorkflowDesignerImpl, {
    name: 'VisualWorkflowDesigner',
    category: 'workflow',
    portal: 'shared',
    version: '1.0.0',
    description: 'Visual drag-and-drop workflow designer',
  })
);

export default VisualWorkflowDesigner;