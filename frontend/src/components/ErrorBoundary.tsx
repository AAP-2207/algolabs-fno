import { Component } from "react";
import type { ErrorInfo, ReactNode } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";

interface Props {
  children?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught error in ErrorBoundary:", error, errorInfo);
  }

  public handleReset = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="flex-1 flex items-center justify-center bg-zinc-950 p-8 min-h-[400px]">
          <Card className="max-w-md w-full bg-zinc-900 border-zinc-800">
            <CardHeader>
              <CardTitle className="text-rose-500 font-bold text-lg">
                Something went wrong
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-zinc-400 text-sm">
                An unexpected error occurred while rendering the derivatives data desk.
              </p>
              {this.state.error && (
                <pre className="p-3 bg-zinc-950 rounded border border-zinc-800 text-xs font-mono text-zinc-500 overflow-auto max-h-40">
                  {this.state.error.message || this.state.error.toString()}
                </pre>
              )}
              <Button
                onClick={this.handleReset}
                variant="outline"
                className="w-full border-zinc-800 hover:bg-zinc-800 text-zinc-300"
              >
                Reload Application
              </Button>
            </CardContent>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}
export default ErrorBoundary;
