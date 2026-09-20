import { Component } from "react";

function reload(event) {
  event.preventDefault();
  window.location.reload();
}

/**
 * Renders its children, or a short notice in their place if they throw while rendering, so one failing part of the
 * page leaves the rest readable. `id` is kept on the notice so links to the part still land.
 */
export default class SectionBoundary extends Component {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <section className="section" id={this.props.id}>
        <div className="wrap">
          <p className="pending">
            This section could not be shown.{" "}
            <a href="" onClick={reload}>
              Reload the page
            </a>{" "}
            to try again.
          </p>
        </div>
      </section>
    );
  }
}
