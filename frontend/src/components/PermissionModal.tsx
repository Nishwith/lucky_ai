import { useState } from "react";
import { useLucky } from "../context/LuckyContext";
import { ShieldAlert, Check, X } from "lucide-react";
import "./PermissionModal.css";

export const PermissionModal = () => {
  const { pendingPermissions, respondToPermission } = useLucky();
  const [remember, setRemember] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (pendingPermissions.length === 0) return null;

  // Display the first request in the queue to handle multiple sequentials cleanly
  const currentRequest = pendingPermissions[0];
  const { request_id, tool_name, params } = currentRequest;

  // Retrieve user-friendly texts for registered tools
  const getToolMetadata = (name: string) => {
    switch (name) {
      case "create_file":
        return {
          title: "Create File",
          desc: "Writes code or structural content to a new file in your workspace.",
          level: "CONFIRM",
        };
      case "delete_file":
        return {
          title: "Delete File",
          desc: "Permanently deletes a file from your local workspace.",
          level: "CONFIRM",
        };
      case "edit_file":
        return {
          title: "Edit File",
          desc: "Modifies contents of an existing file by finding and replacing a block of text.",
          level: "CONFIRM",
        };
      case "create_folder":
        return {
          title: "Create Folder",
          desc: "Creates a new subdirectory tree inside the workspace root.",
          level: "CONFIRM",
        };
      case "run_command":
        return {
          title: "Run Terminal Command",
          desc: "Executes a shell command in the workspace directory context.",
          level: "CONFIRM",
        };
      case "run_python":
        return {
          title: "Run Python Script",
          desc: "Runs arbitrary Python scripts inside the current system environment.",
          level: "CONFIRM",
        };
      case "scaffold_project":
        return {
          title: "Scaffold Project",
          desc: "Generates boilerplate structure and code files matching a starter template.",
          level: "CONFIRM",
        };
      default:
        return {
          title: name,
          desc: "Executes a registered system operating tool.",
          level: "CONFIRM",
        };
    }
  };

  const meta = getToolMetadata(tool_name);

  const handleAction = async (approved: boolean) => {
    setIsSubmitting(true);
    const rule = remember ? (approved ? "allow" : "deny") : null;
    await respondToPermission(request_id, approved, rule);
    setIsSubmitting(false);
    setRemember(false); // Reset for next item in the queue
  };

  return (
    <div className="permission-modal-overlay">
      <div className="permission-modal-card">
        <div className="permission-modal-header">
          <div className="permission-icon-container">
            <ShieldAlert size={22} className="warning-icon" />
          </div>
          <div className="header-text">
            <h3>Authorization Required</h3>
            <p className="subtitle">LUCKY is requesting permission to execute an OS operation</p>
          </div>
        </div>

        <div className="permission-modal-body">
          <div className="meta-grid">
            <div className="meta-row">
              <span className="meta-label">Operation:</span>
              <span className="meta-value tool-badge">{meta.title}</span>
            </div>
            <div className="meta-row">
              <span className="meta-label">Security level:</span>
              <span className="meta-value level-badge confirm-level">{meta.level}</span>
            </div>
          </div>

          <div className="description-container">
            <p className="description-text">{meta.desc}</p>
          </div>

          <div className="parameters-container">
            <div className="param-header">Parameters:</div>
            <pre className="param-code">
              {JSON.stringify(params, null, 2)}
            </pre>
          </div>

          <div className="remember-checkbox-container">
            <label className="remember-label">
              <input
                type="checkbox"
                checked={remember}
                onChange={(e) => setRemember(e.target.checked)}
              />
              <span className="remember-text">
                Remember decision (Always Allow / Always Deny for this tool)
              </span>
            </label>
          </div>
        </div>

        <div className="permission-modal-actions">
          <button
            className="btn-action btn-deny"
            disabled={isSubmitting}
            onClick={() => handleAction(false)}
          >
            <X size={15} />
            <span>Deny</span>
          </button>
          <button
            className="btn-action btn-allow"
            disabled={isSubmitting}
            onClick={() => handleAction(true)}
          >
            <Check size={15} />
            <span>Allow</span>
          </button>
        </div>
      </div>
    </div>
  );
};
