"""
CodeGraph AI - AI Review Module
Provides provider-independent architecture and security review.
Features a comprehensive, deterministic rule-based engine as well as
optional Google Gemini and OpenAI integrations.
"""

from typing import Dict, Any, List, Optional
import json
import logging
import httpx
from backend.app.config import settings

logger = logging.getLogger("codegraph.ai")


class BaseAIProvider:
    """Abstract interface for AI code architecture review."""
    def generate_review(self, summary: Dict[str, Any], findings: List[Dict[str, Any]]) -> Dict[str, Any]:
        raise NotImplementedError


class RuleBasedAIProvider(BaseAIProvider):
    """
    Deterministic rule-based review engine that synthesizes real architecture metrics
    and security findings into a comprehensive professional report without any external API.
    """

    def generate_review(self, summary: Dict[str, Any], findings: List[Dict[str, Any]]) -> Dict[str, Any]:
        project_name = summary.get("project_name", "Codebase")
        files_cnt = summary.get("file_counts", 0)
        symbols_cnt = summary.get("symbol_counts", 0)
        pkgs_cnt = summary.get("package_counts", 0)
        sev_counts = summary.get("security_severity_counts", {"HIGH": 0, "MEDIUM": 0, "LOW": 0})
        hotspots = summary.get("dependency_hotspots", [])
        circular = summary.get("circular_dependencies", [])
        top_pkgs = summary.get("top_packages", [])
        largest_files = summary.get("largest_files", [])

        # 1. Architecture Overview
        arch_overview = (
            f"The project '{project_name}' comprises {files_cnt} source files, defining {symbols_cnt} "
            f"functions and classes, and utilizing {pkgs_cnt} external third-party packages. "
        )
        if files_cnt > 20:
            arch_overview += "The codebase exhibits a multi-module architecture with distinct subcomponents."
        elif files_cnt > 0:
            arch_overview += "The codebase exhibits a focused, compact architecture with direct file couplings."
        else:
            arch_overview += "The repository contains minimal recognized source code."

        # 2. Key Dependencies & Hubs
        key_deps = []
        if hotspots:
            top_hub = hotspots[0]
            key_deps.append(
                f"Primary architectural hub is '{top_hub['path']}' with {top_hub.get('in_degree', 0)} incoming "
                f"and {top_hub.get('out_degree', 0)} outgoing file connections."
            )
            for h in hotspots[1:4]:
                key_deps.append(
                    f"Coupled module '{h['path']}' (total dependencies: {h.get('total_deps', 0)})."
                )
        if top_pkgs:
            pkg_names = [p["name"] for p in top_pkgs[:5]]
            key_deps.append(f"Most frequent external package integrations: {', '.join(pkg_names)}.")

        # 3. Security Concerns
        security_concerns = []
        high_count = sev_counts.get("HIGH", 0)
        med_count = sev_counts.get("MEDIUM", 0)
        low_count = sev_counts.get("LOW", 0)

        if high_count > 0:
            security_concerns.append(
                f"Critical/High Severity: Detected {high_count} high-severity issue(s) requiring immediate remediation."
            )
        if med_count > 0:
            security_concerns.append(
                f"Moderate Exposure: Detected {med_count} medium-severity issue(s) that could increase attack surface."
            )
        if low_count > 0:
            security_concerns.append(
                f"Hardening Opportunities: Detected {low_count} low-severity issue(s) or informational indicators."
            )
        if not security_concerns:
            security_concerns.append("No overt static security anti-patterns flagged by the scanner.")

        # 4. Concrete Recommendations
        recommendations = []
        seen_rules = set()
        for fd in findings:
            r_id = fd.get("rule_id")
            if r_id and r_id not in seen_rules:
                seen_rules.add(r_id)
                recommendations.append({
                    "title": f"Remediate {r_id} in {fd.get('file', 'codebase')}",
                    "category": "Security Hardening",
                    "severity": fd.get("severity", "MEDIUM"),
                    "details": f"{fd.get('message', '')} Recommendation: {fd.get('recommendation', '')}"
                })

        # Circular dependencies recommendation
        if circular:
            recommendations.append({
                "title": "Decouple Circular Import Chains",
                "category": "Architecture Health",
                "severity": "MEDIUM",
                "details": f"Found {len(circular)} circular import cycle(s). Refactor shared contracts or models into standalone interface modules to prevent runtime import deadlocks."
            })

        # 5. Refactoring Priorities
        refactoring_priorities = []
        if circular:
            refactoring_priorities.append(
                f"Eliminate {len(circular)} circular dependency loop(s) starting with: {' -> '.join(circular[0])}."
            )
        if hotspots:
            refactoring_priorities.append(
                f"Decompose hotspot module '{hotspots[0]['path']}' to reduce high coupling."
            )
        if largest_files and largest_files[0].get("loc", 0) > 300:
            refactoring_priorities.append(
                f"Split oversized file '{largest_files[0]['path']}' ({largest_files[0]['loc']} lines) into focused sub-modules."
            )
        if not refactoring_priorities:
            refactoring_priorities.append("Codebase structure is balanced; maintain separation of concerns as features expand.")

        # 6. Circular Import Observations
        if circular:
            cycle_desc = "The following circular dependency chains were observed:\n"
            for idx, c in enumerate(circular, 1):
                cycle_desc += f"{idx}. " + " -> ".join(c) + "\n"
        else:
            cycle_desc = "No circular import chains were detected. Dependency graph forms a clean Directed Acyclic Graph (DAG)."

        # 7. Limitations & Uncertainty
        limitations = (
            "Static analysis heuristics provide indicators of potential risk and coupling, not absolute proof of exploitability. "
            "Dynamic reflection, runtime framework dependency injection, and eval-like imports may not be fully resolved."
        )

        # Markdown synthesis
        md_report = f"""# CodeGraph AI Architecture & Security Review
**Project:** {project_name}  
**Engine:** Rule-Based Deterministic Analyzer (Offline Mode)  

---

## 1. Architectural Overview
{arch_overview}

## 2. Key Modules & Dependency Distribution
"""
        for kd in key_deps:
            md_report += f"- {kd}\n"

        md_report += f"""
## 3. Security Concerns & Vulnerability Surface
"""
        for sc in security_concerns:
            md_report += f"- {sc}\n"

        md_report += f"""
## 4. Prioritized Refactoring Guidance
"""
        for rp in refactoring_priorities:
            md_report += f"- {rp}\n"

        md_report += f"""
## 5. Circular Dependency Analysis
{cycle_desc}

## 6. Actionable Recommendations
"""
        for rec in recommendations[:8]:
            md_report += f"### [{rec['severity']}] {rec['title']}\n{rec['details']}\n\n"

        md_report += f"""
---
> **Analysis Notice:** {limitations}
"""

        return {
            "project_id": summary.get("project_id", ""),
            "provider_used": "rule-based-engine",
            "is_fallback": True,
            "architecture_overview": arch_overview,
            "key_dependencies": key_deps,
            "security_concerns": security_concerns,
            "recommendations": recommendations,
            "refactoring_priorities": refactoring_priorities,
            "circular_import_observations": cycle_desc,
            "limitations_and_uncertainty": limitations,
            "raw_markdown": md_report
        }


class ExternalAIProvider(BaseAIProvider):
    """Integrates with Google Gemini or OpenAI when credentials are provided."""

    def __init__(self, provider: str, api_key: str, model: str):
        self.provider = provider.lower()
        self.api_key = api_key
        self.model = model or ("gemini-1.5-flash" if self.provider == "gemini" else "gpt-4o-mini")

    def generate_review(self, summary: Dict[str, Any], findings: List[Dict[str, Any]]) -> Dict[str, Any]:
        prompt = (
            "You are a senior software architect and cybersecurity auditor. Analyze the following codebase "
            "graph summary and security scanner findings. Return a structured JSON response with keys: "
            "architecture_overview, key_dependencies (list), security_concerns (list), "
            "recommendations (list of objects with title, category, severity, details), "
            "refactoring_priorities (list), circular_import_observations, limitations_and_uncertainty, raw_markdown.\n\n"
            f"SUMMARY DATA:\n{json.dumps(summary, indent=2)}\n\n"
            f"SAMPLE FINDINGS (up to 15):\n{json.dumps(findings[:15], indent=2)}"
        )

        try:
            if self.provider == "gemini":
                # Google Gemini REST API call
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}
                }
                with httpx.Client(timeout=25.0) as client:
                    resp = client.post(url, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    text_content = data["candidates"][0]["content"]["parts"][0]["text"]
                    parsed = json.loads(text_content)
                    parsed["project_id"] = summary.get("project_id", "")
                    parsed["provider_used"] = f"gemini ({self.model})"
                    parsed["is_fallback"] = False
                    return parsed

            elif self.provider == "openai":
                # OpenAI REST API call
                url = "https://api.openai.com/v1/chat/completions"
                headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "You are a software architecture and security reviewer. Respond in JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    "response_format": {"type": "json_object"}
                }
                with httpx.Client(timeout=25.0) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    text_content = data["choices"][0]["message"]["content"]
                    parsed = json.loads(text_content)
                    parsed["project_id"] = summary.get("project_id", "")
                    parsed["provider_used"] = f"openai ({self.model})"
                    parsed["is_fallback"] = False
                    return parsed

        except Exception as e:
            logger.warning(f"External AI request failed ({e}), falling back to deterministic rule-based engine.")

        # Fallback to rule-based if external call fails or raises
        fallback = RuleBasedAIProvider().generate_review(summary, findings)
        fallback["provider_used"] = f"{self.provider} (failed: fallback to rule-based)"
        return fallback


def get_ai_reviewer() -> BaseAIProvider:
    """Factory creating appropriate AI reviewer based on environment configuration."""
    if settings.AI_PROVIDER in ("gemini", "openai") and settings.AI_API_KEY:
        return ExternalAIProvider(
            provider=settings.AI_PROVIDER,
            api_key=settings.AI_API_KEY,
            model=settings.AI_MODEL
        )
    return RuleBasedAIProvider()
