import { render, screen } from '@testing-library/react'
import Home from '../app/page'

describe('Home', () => {
  it('renders without crashing', () => {
    render(<Home />)
    expect(screen.getByText(/exlm/i)).toBeInTheDocument()
  })

  it('displays welcome message', () => {
    render(<Home />)
    expect(screen.getByText(/Domain-Specific LLM Automation Platform/i)).toBeInTheDocument()
  })
}) 