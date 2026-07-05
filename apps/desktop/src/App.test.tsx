import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { App } from './App';

describe('App', () => {
  it('renders the Bolt workbench shell', () => {
    render(<App />);

    expect(screen.getByText('Bolt')).toBeInTheDocument();
    expect(screen.getByText('Agent Core')).toBeInTheDocument();
    expect(screen.getByText('No workspace selected')).toBeInTheDocument();
    expect(screen.getByText('Task Log')).toBeInTheDocument();
    expect(screen.getByText('Harness Trace')).toBeInTheDocument();
    expect(screen.getByText('Pending Permissions')).toBeInTheDocument();
    expect(screen.getByText('Memory')).toBeInTheDocument();
    expect(screen.getByText('No execution results.')).toBeInTheDocument();
  });

  it('starts with a product-focused assistant message', () => {
    render(<App />);

    expect(screen.getByText(/安全代码助手已就绪/)).toBeInTheDocument();
  });
});
