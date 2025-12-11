import { render, screen, fireEvent, within } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import NetworkInsightsPanel from './NetworkInsightsPanel';
import { NetworkInsights } from '../../types/query';

describe('NetworkInsightsPanel', () => {
  const mockInsights: NetworkInsights = {
    skill_paths: [
      {
        from_skill: 'Java',
        to_skill: 'Backend Developer',
        path: ['Java', 'Spring', 'Backend Developer'],
        total_cost: 0.5,
        closeness: 0.95
      }
    ],
    similar_jobs: [
      {
        job_id: '1',
        job_title: 'Senior Developer',
        company: 'Tech Corp',
        jaccard_score: 0.85,
        shared_skills: ['Java', 'Spring']
      }
    ],
    top_skills: [
      {
        skill_name: 'React',
        canonical_name: 'react',
        centrality: 8.5,
        demand_count: 10
      }
    ],
    transition_feasibility: 0.9
  };

  it('renders nothing when no insights provided', () => {
    const { container } = render(<NetworkInsightsPanel insights={null as any} />); 
    expect(container).toBeEmptyDOMElement();
  });

  it('renders "Network Insights" header when insights provided', () => {
    render(<NetworkInsightsPanel insights={mockInsights} />);
    expect(screen.getByText('Network Insights')).toBeInTheDocument();
  });

  it('renders default expanded sections (Job Fit)', () => {
    render(<NetworkInsightsPanel insights={mockInsights} />);
    // Job Fit should be visible
    expect(screen.getByText('Job Fit Analysis')).toBeInTheDocument();
  });

  it('renders default Job Fit Analysis content', () => {
    render(<NetworkInsightsPanel insights={mockInsights} />);
    // "React" is in top_skills, and our mock logic puts top 3 in "Skills to Learn" and next 2 in "Skills You Have"
    // Since we only have 1 top skill in mock, it goes to "Skills to Learn"
    
    // We expect "Skills to Learn" section to contain "React"
    expect(screen.getByText('Skills to Learn')).toBeInTheDocument();
    
    // Verify React is present
    const learnSection = screen.getByText('Skills to Learn').closest('div')?.parentElement;
    expect(learnSection).toBeDefined();
    if (learnSection) {
       expect(within(learnSection).getByText('React')).toBeInTheDocument();
    }
  });

  it('expands and collapses sections on click', () => {
    render(<NetworkInsightsPanel insights={mockInsights} />);
    
    // Skill Paths initially collapsed
    expect(screen.queryByText('Route Confidence')).not.toBeInTheDocument();
    
    // Expand Skill Paths
    fireEvent.click(screen.getByText('Skill Bridge Paths'));
    expect(screen.getByText('Route Confidence')).toBeInTheDocument();
    
    // Collapse Skill Paths
    fireEvent.click(screen.getByText('Skill Bridge Paths'));
    // wait next tick if needed, but standard React state update is usually synchronous in tests unless transition used
    // With transition-all usually we might need waitFor, but let's try direct check first
    expect(screen.queryByText('Route Confidence')).not.toBeInTheDocument();
  });

  it('renders Similar Jobs section correctly', () => {
    render(<NetworkInsightsPanel insights={mockInsights} />);
    fireEvent.click(screen.getByText('Similar Jobs'));
    
    // Use getAllByText because job title might appear in other contexts theoretically, but here unique enough
    // Scoping is safer
    const jobsSection = screen.getByText('Similar Jobs').closest('div')?.parentElement;
    // The closest div might be the button container, we want the CollapsibleSection container or the content div
    // But simply looking for unique texts is fine
    expect(screen.getByText('Senior Developer')).toBeInTheDocument();
    expect(screen.getByText('Tech Corp')).toBeInTheDocument();
  });

  it('renders Top Skills section correctly', () => {
    render(<NetworkInsightsPanel insights={mockInsights} />);
    fireEvent.click(screen.getByText('Top Skills'));
    
    // React appears in Job Fit and Top Skills. 
    // We should see at least 2 instances of "React" now (one in Job Fit, one in Top Skills)
    const reactElements = screen.getAllByText('React');
    expect(reactElements.length).toBeGreaterThanOrEqual(2);
    
    expect(screen.getByText('8.50 Centrality')).toBeInTheDocument();
  });
});
