export interface ErrorStateProps {
  message: string
}

export function ErrorState({ message }: ErrorStateProps) {
  return (
    <div className="screen state-error" role="alert">
      <p>{message}</p>
    </div>
  )
}
