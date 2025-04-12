#!/bin/bash

# ==============================================================================
# criar_issues_script.sh (v17)
#
# Creates or EDITS GitHub Issues based on a structured text file.
# Correctly uses --add-assignee and -m <title> for gh issue edit.
# If an OPEN issue with the EXACT SAME TITLE exists, it EDITS the most recent one
# (updating body, assignee, milestone, and *adding* specified labels).
# Otherwise, it CREATES a new issue (setting labels).
# Project association is only attempted during CREATION.
# Parses blocks, uses templates. Handles comments. Checks/creates labels/milestones.
# Checks for project existence. Exits on failure if project specified.
#
# Dependencies:
#   - Bash 4.3+ (for namerefs 'declare -n')
#   - gh (GitHub CLI): https://cli.github.com/
#   - jq: https://stedolan.github.io/jq/
#   - sed, awk, tr, rev (standard Unix tools)
#
# Usage:
#   ./criar_issues_script.sh [--milestone-title "Milestone Title"] [--milestone-desc "Milestone Desc"] [input_file]
#
# ==============================================================================

# --- Configuration ---
DEFAULT_INPUT_FILE="planos/plano_dev.txt"
TEMPLATE_DIR="project_templates/issue_bodies"
DEFAULT_TEMPLATE="default_body.md"
DEFAULT_LABEL="todo"
DEFAULT_ASSIGNEE="@me"
DEFAULT_LABEL_COLOR="ededed"
# REPO_TARGET="owner/repo" # Optional: Specify if not running in repo dir.
REPO_TARGET=""
PROJECT_PRIMARY_OWNER="@me" # First place to look for projects
ISSUE_LIST_LIMIT=500       # How many recent open issues to fetch for duplicate checking

# --- Script Variables ---
arg_milestone_title=""
arg_milestone_desc=""
input_file_arg=""
milestone_mandatory=false
global_milestone_title_to_use=""
declare -A checked_labels
repo_owner=""

# --- Helper Functions ---
command_exists() { command -v "$1" >/dev/null 2>&1; }
trim() { local var="$*"; var="${var#"${var%%[![:space:]]*}"}"; var="${var%"${var##*[![:space:]]}"}"; printf '%s' "$var"; }
escape_for_jq_string() { printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'; }
escape_for_sed_replacement() { local escaped; escaped=$(printf '%s' "$1" | sed -e 's/[\\|&]/\\&/g'); escaped=$(printf '%s' "$escaped" | awk '{printf "%s\\n", $0}' | sed '$s/\\n$//'); printf '%s' "$escaped"; }

check_and_create_label() {
    local label_name="$1"; declare -n repo_flags_array_ref=$2; local existing_label list_exit_code create_exit_code escaped_label_name jq_filter
    if [[ -v checked_labels["$label_name"] ]]; then [[ "${checked_labels[$label_name]}" != "failed_creation" ]]; return $?; fi
    set +e; escaped_label_name=$(escape_for_jq_string "$label_name"); jq_filter=".[] | select(.name == \"$escaped_label_name\")"
    existing_label=$(gh label list "${repo_flags_array_ref[@]}" --search "$label_name" --json name --jq "$jq_filter" 2>/dev/null); list_exit_code=$?; set -e
    if [[ $list_exit_code -ne 0 ]]; then echo >&2 "    Warning: Failed check label '$label_name' (Code: $list_exit_code). Assuming non-existent."; existing_label=""; fi
    if [[ -z "$existing_label" ]]; then
        echo "    Label '$label_name' not found. Creating..."
        echo "      Executing: gh label create \"$label_name\" ${repo_flags_array_ref[@]} --color \"$DEFAULT_LABEL_COLOR\" --description \"Created by script\""
        gh label create "$label_name" "${repo_flags_array_ref[@]}" --color "$DEFAULT_LABEL_COLOR" --description "Created by script"; create_exit_code=$?
        if [[ $create_exit_code -ne 0 ]]; then echo >&2 "    Error: Failed create label '$label_name' (Code: $create_exit_code)."; checked_labels["$label_name"]="failed_creation"; return 1;
        else echo "    Label '$label_name' created."; checked_labels["$label_name"]="created"; fi
    else checked_labels["$label_name"]="exists"; fi
    return 0
}

# --- Dependency Checks ---
if (( BASH_VERSINFO[0] < 4 || (BASH_VERSINFO[0] == 4 && BASH_VERSINFO[1] < 3) )); then echo >&2 "Error: Bash 4.3+ required."; exit 1; fi
for cmd in gh jq sed awk tr rev; do if ! command_exists "$cmd"; then echo >&2 "Error: Required command '$cmd' not found."; exit 1; fi; done

# --- Argument Parsing ---
while [[ $# -gt 0 ]]; do key="$1"; case $key in --milestone-title) arg_milestone_title="$2"; milestone_mandatory=true; shift 2 ;; --milestone-desc) arg_milestone_desc="$2"; milestone_mandatory=true; shift 2 ;; *) if [[ -z "$input_file_arg" && ! "$key" =~ ^-- ]]; then input_file_arg="$1"; shift; else echo "Warning: Ignoring unknown option: $1" >&2; shift; fi ;; esac; done
INPUT_FILE="${input_file_arg:-$DEFAULT_INPUT_FILE}"
if $milestone_mandatory && [[ -z "$arg_milestone_title" ]]; then echo >&2 "Error: --milestone-title required."; exit 1; fi

# --- Repository Flag & Determine Repo Owner ---
repo_flag_array=(); if [[ -n "$REPO_TARGET" ]]; then repo_flag_array+=("-R" "$REPO_TARGET"); echo "Targeting repository: $REPO_TARGET"; repo_owner=$(echo "$REPO_TARGET" | cut -d/ -f1); if [[ -z "$repo_owner" || "$repo_owner" == "$REPO_TARGET" ]]; then echo >&2 "Error: Could not determine owner from REPO_TARGET '$REPO_TARGET'."; exit 1; fi; else echo "Using current repository."; set +e; echo "  Executing: gh repo view --json owner --jq .owner.login"; repo_owner=$(gh repo view --json owner --jq .owner.login 2>/dev/null); repo_view_exit_code=$?; set -e; if [[ $repo_view_exit_code -ne 0 || -z "$repo_owner" ]]; then echo >&2 "Error: Failed to determine owner of current repository (Code: $repo_view_exit_code)."; exit 1; fi; fi; echo "Determined repo owner: $repo_owner"

# --- Milestone Handling ---
if $milestone_mandatory; then
    echo "--- Milestone Check ---"; echo "Milestone specified: '$arg_milestone_title'"
    echo "Looking up milestone..."; milestone_found=false; set +e; escaped_milestone_title=$(escape_for_jq_string "$arg_milestone_title"); jq_filter_milestone_check=".[] | select(.title == \"$escaped_milestone_title\") | .number"
    echo "  Executing: gh milestone list ${repo_flag_array[@]} --json title,number --jq '$jq_filter_milestone_check'"; existing_milestone_num=$(gh milestone list "${repo_flag_array[@]}" --json title,number --jq "$jq_filter_milestone_check" 2>/dev/null); lookup_exit_code=$?; set -e
    if [[ $lookup_exit_code -ne 0 ]]; then echo >&2 "Error: Failed 'gh milestone list' (Code: $lookup_exit_code)."; exit 1; fi
    if [[ -n "$existing_milestone_num" ]]; then echo "Milestone '$arg_milestone_title' found."; milestone_found=true; global_milestone_title_to_use="$arg_milestone_title";
    else
        echo "Milestone '$arg_milestone_title' not found."
        if [[ -n "$arg_milestone_desc" ]]; then
            echo "Attempting to create milestone '$arg_milestone_title'..."; echo "  Executing: gh milestone create --title \"$arg_milestone_title\" --description \"$arg_milestone_desc\" ${repo_flag_array[@]}"
            gh milestone create --title "$arg_milestone_title" --description "$arg_milestone_desc" "${repo_flag_array[@]}"; create_exit_code=$?
            if [[ $create_exit_code -eq 0 ]]; then echo "Milestone possibly created. Using title '$arg_milestone_title' for association."; milestone_found=true; global_milestone_title_to_use="$arg_milestone_title";
            else echo >&2 "Error: Failed to create milestone '$arg_milestone_title' (Code: $create_exit_code)."; exit 1; fi
        else echo >&2 "Error: Milestone '$arg_milestone_title' not found and --milestone-desc missing."; exit 1; fi
    fi; if ! $milestone_found ; then echo >&2 "Error: Failed find/create mandatory milestone '$arg_milestone_title'."; exit 1; fi
    echo "--- End Milestone Check ---"
fi

# --- File and Template Directory Checks ---
if [ ! -f "$INPUT_FILE" ]; then echo >&2 "Error: Input file '$INPUT_FILE' not found."; exit 1; fi
if [ ! -d "$TEMPLATE_DIR" ]; then echo >&2 "Error: Template directory '$TEMPLATE_DIR' not found."; exit 1; fi

# --- Main Processing Logic ---
echo "Starting GitHub Issue processing from '$INPUT_FILE'..."

awk 'BEGIN{RS="------\n"; ORS="\0"} {print $0}' "$INPUT_FILE" | while IFS= read -r -d $'\0' block; do
    if [[ -z "${block//[[:space:]]/}" ]]; then continue; fi
    echo "----------------------------------------"; echo "Processing Block:"
    declare -A issue_data; declare -a body_placeholders; current_key=""; multiline_value=""

    # Parse KEY: VALUE pairs (Handles comments)
    while IFS= read -r line; do
        trimmed_line=$(trim "$line"); if [[ "$trimmed_line" =~ ^([A-Z_]+):(.*)$ ]]; then
        if [[ -n "$current_key" && -n "$multiline_value" ]]; then if [[ "$current_key" != "MILESTONE" ]]; then multiline_value_cleaned=$(echo "$multiline_value" | sed 's/#.*$//'); issue_data["$current_key"]=$(trim "${issue_data[$current_key]}"$'\n'"${multiline_value_cleaned}"); fi; fi
        current_key="${BASH_REMATCH[1]}"; raw_value="${BASH_REMATCH[2]}"; value_no_comment="${raw_value%%#*}"; value=$(trim "$value_no_comment"); if [[ "$current_key" == "MILESTONE" ]]; then echo >&2 "  Info: MILESTONE key ignored in block."; current_key=""; continue; fi
        issue_data["$current_key"]="$value"; multiline_value=""; if [[ "$current_key" != "TITLE" && "$current_key" != "TYPE" && "$current_key" != "LABELS" && "$current_key" != "ASSIGNEE" && "$current_key" != "PROJECT" ]]; then body_placeholders+=("$current_key"); fi
        elif [[ -n "$current_key" && "$current_key" != "MILESTONE" && ! "$trimmed_line" =~ ^# ]]; then if [[ -z "$multiline_value" ]]; then multiline_value="$line"; else multiline_value+=$'\n'"$line"; fi; fi
    done <<< "$block"
    if [[ -n "$current_key" && -n "$multiline_value" ]]; then if [[ "$current_key" != "MILESTONE" ]]; then multiline_value_cleaned=$(echo "$multiline_value" | sed 's/#.*$//'); issue_data["$current_key"]=$(trim "${issue_data[$current_key]}"$'\n'"${multiline_value_cleaned}"); fi; fi

    # Validate Title
    TITLE="${issue_data[TITLE]:-}"; if [[ -z "$TITLE" ]]; then echo >&2 "Warning: Skipping block due to missing TITLE."; continue; fi
    echo "  Issue Title: $TITLE"

    # Determine Type and Template
    TYPE="${issue_data[TYPE]:-default}"; issue_type_lower=$(echo "$TYPE" | tr '[:upper:]' '[:lower:]')
    if [[ "$TYPE" == "default" ]]; then echo >&2 "  Info: TYPE missing/invalid for '$TITLE'. Using 'default'."; fi
    template_file=""; if [[ -f "$TEMPLATE_DIR/${issue_type_lower}_body.md" ]]; then template_file="$TEMPLATE_DIR/${issue_type_lower}_body.md"; elif [[ ("$issue_type_lower" == "chore" || "$issue_type_lower" == "refactor") && -f "$TEMPLATE_DIR/chore_body.md" ]]; then template_file="$TEMPLATE_DIR/chore_body.md"; elif [[ -f "$TEMPLATE_DIR/$DEFAULT_TEMPLATE" ]]; then echo "  Info: Template '$issue_type_lower' not found. Using '$DEFAULT_TEMPLATE'."; template_file="$TEMPLATE_DIR/$DEFAULT_TEMPLATE"; else echo "  Warning: No template found. Using generic body."; template_file=""; fi

    # Prepare Issue Body
    issue_body=""; if [[ -n "$template_file" && -f "$template_file" ]]; then issue_body=$(<"$template_file"); processed_keys=(); for key in "${!issue_data[@]}"; do if [[ " ${body_placeholders[*]} " =~ " ${key} " && ! " ${processed_keys[*]} " =~ " ${key} " ]]; then placeholder="__${key}__"; value="${issue_data[$key]:-}"; value_escaped=$(escape_for_sed_replacement "$value"); issue_body=$(sed "s|${placeholder}|${value_escaped}|g" <<< "$issue_body"); processed_keys+=("$key"); fi; done; issue_body=$(sed 's|__[A-Z_]\+__|[Not Provided]|g' <<< "$issue_body"); else issue_body="Issue created from script for title: $TITLE"; fi

    # --- Check for Existing Issue (Robust Method) ---
    echo "  Checking for existing open issue with title '$TITLE'..."
    existing_issue_num=""; list_output=""; list_error=""; set +e; escaped_title_jq=$(escape_for_jq_string "$TITLE"); jq_filter_list='map(select(.title == "'"$escaped_title_jq"'" and .state == "OPEN")) | sort_by(.updatedAt) | reverse | .[0].number // empty'; list_cmd_str="gh issue list ${repo_flag_array[@]} --state open --limit $ISSUE_LIST_LIMIT --json number,title,state,updatedAt"
    # echo "    Executing: $list_cmd_str" # Reduce noise
    list_output=$( $list_cmd_str 2> >(list_error=$(cat); declare -p list_error >&2) ); list_exit_code=$?; declare -p list_error > /dev/null; set -e
    if [[ $list_exit_code -ne 0 ]]; then echo >&2 "    Warning: Failed check for existing issues (Code: $list_exit_code). Proceeding with creation."; echo >&2 "    Command: $list_cmd_str"; if [[ -n "$list_output" ]]; then echo >&2 "    Stdout: $list_output"; fi; if [[ -n "$list_error" ]]; then echo >&2 "    Stderr: $list_error"; fi; existing_issue_num="";
    else
        set +e; existing_issue_num=$(jq -r "$jq_filter_list" <<< "$list_output"); jq_exit_code=$?; set -e
        if [[ $jq_exit_code -ne 0 ]]; then echo >&2 "    Warning: jq processing failed (Code: $jq_exit_code). Proceeding with creation."; echo >&2 "    gh output was: $list_output"; existing_issue_num=""; fi
    fi

    # --- Prepare Labels (For both create/edit) ---
    labels_to_apply_array=() # Holds the actual label names to be applied
    labels_str="${issue_data[LABELS]:-}"; IFS=',' read -r -a labels_array <<< "$labels_str"; has_labels=false
    for label in "${labels_array[@]}"; do trimmed_label=$(trim "$label"); if [[ -n "$trimmed_label" ]]; then if check_and_create_label "$trimmed_label" "repo_flag_array"; then labels_to_apply_array+=("$trimmed_label"); has_labels=true; else echo >&2 "  Skipping label '$trimmed_label' for '$TITLE'."; fi; fi; done
    type_label=$(trim "$TYPE"); if [[ "$issue_type_lower" != "default" && ! " ${labels_array[*]} " =~ " ${type_label} " ]]; then if check_and_create_label "$type_label" "repo_flag_array"; then labels_to_apply_array+=("$type_label"); has_labels=true; else echo >&2 "  Skipping type label '$type_label' for '$TITLE'."; fi; fi
    if ! $has_labels && [[ -n "$DEFAULT_LABEL" ]]; then if check_and_create_label "$DEFAULT_LABEL" "repo_flag_array"; then labels_to_apply_array+=("$DEFAULT_LABEL"); else echo >&2 "  Skipping default label '$DEFAULT_LABEL' for '$TITLE'."; fi; fi

    # --- Prepare Assignee and Milestone ---
    assignee_value="${issue_data[ASSIGNEE]:-$DEFAULT_ASSIGNEE}"
    milestone_title_value="$global_milestone_title_to_use" # Use the globally determined title

    # --- Execute Edit or Create ---
    if [[ -n "$existing_issue_num" ]]; then
        # --- EDIT EXISTING ISSUE ---
        echo "  Existing open issue found (#$existing_issue_num). Editing..."
        edit_flags_array=() # Flags specific to edit command

        # Add assignee using --add-assignee
        if [[ -n "$assignee_value" ]]; then
            edit_flags_array+=("--add-assignee" "$assignee_value")
        fi

        # Add milestone using -m <title>
        if [[ -n "$milestone_title_value" ]]; then
             edit_flags_array+=("-m" "$milestone_title_value")
        elif $milestone_mandatory; then
             # This check might be redundant if initial check passed, but safe
             echo >&2 "Error: Mandatory milestone unavailable for editing issue '$TITLE'."; continue;
        fi

        # Add labels using --add-label
        for label in "${labels_to_apply_array[@]}"; do
            edit_flags_array+=("--add-label" "$label")
        done

        # Construct command string for echoing
        cmd_str="printf '%s' \"\$issue_body\" | gh issue edit $existing_issue_num -F -"
        for flag in "${edit_flags_array[@]}"; do cmd_str+=" '$flag'"; done
        for flag in "${repo_flag_array[@]}"; do cmd_str+=" '$flag'"; done
        echo "    Executing: $cmd_str"

        # Execute the edit command
        printf '%s' "$issue_body" | gh issue edit "$existing_issue_num" -F - "${edit_flags_array[@]}" "${repo_flag_array[@]}"; edit_exit_code=$?
        if [[ $edit_exit_code -eq 0 ]]; then echo "    Issue #$existing_issue_num edited successfully."; if [[ -n "${issue_data[PROJECT]:-}" ]]; then echo "    Info: Project association skipped during edit. Verify/add manually: Project '${issue_data[PROJECT]}'"; fi
        else echo >&2 "    Error editing issue #$existing_issue_num (Code: $edit_exit_code)."; fi

    else
        # --- CREATE NEW ISSUE ---
        echo "  No existing open issue found with this title. Creating..."
        # Prepare project flag (only for creation)
        project_flag_array=(); project_name_or_num="${issue_data[PROJECT]:-}";
        if [[ -n "$project_name_or_num" ]]; then
            project_found=false; set +e; escaped_project_name=$(escape_for_jq_string "$project_name_or_num"); jq_filter_project=".projects[] | select(.title == \"$escaped_project_name\" or (.number | tostring) == \"$escaped_project_name\") | .id";
            project_id=$(gh project list --owner "$PROJECT_PRIMARY_OWNER" --format json --jq "$jq_filter_project" 2>/dev/null | head -n 1); project_lookup_exit_code=$?; set -e
            if [[ $project_lookup_exit_code -eq 0 && -n "$project_id" ]]; then project_to_add="$project_name_or_num"; project_found=true;
            else if [[ "$PROJECT_PRIMARY_OWNER" != "$repo_owner" ]]; then set +e; project_id=$(gh project list --owner "$repo_owner" --format json --jq "$jq_filter_project" 2>/dev/null | head -n 1); project_lookup_exit_code=$?; set -e; if [[ $project_lookup_exit_code -eq 0 && -n "$project_id" ]]; then project_to_add="$project_name_or_num"; project_found=true; fi; fi; fi
            if $project_found; then echo "    Will add issue to project '$project_to_add'."; project_flag_array+=("-p" "$project_to_add");
            else echo >&2 "Error: Project '$project_name_or_num' not found. Cannot create issue '$TITLE'."; continue; fi # Skip issue
        fi

        # Prepare all flags for creation
        create_flags_array=("-t" "$TITLE") # Start with title

        # Add assignee using -a
        if [[ -n "$assignee_value" ]]; then
            create_flags_array+=("-a" "$assignee_value")
        fi

        # Add milestone using -m <title>
        if [[ -n "$milestone_title_value" ]]; then
             create_flags_array+=("-m" "$milestone_title_value")
        elif $milestone_mandatory; then
             echo >&2 "Error: Mandatory milestone unavailable for creating issue '$TITLE'."; continue;
        fi

        # Add labels using -l
        for label in "${labels_to_apply_array[@]}"; do
            create_flags_array+=("-l" "$label")
        done

        create_flags_array+=("${project_flag_array[@]}")  # Project (if found)
        create_flags_array+=("${repo_flag_array[@]}")     # Repository

        # Construct command string for echoing
        cmd_str="printf '%s' \"\$issue_body\" | gh issue create -F -"
        for flag in "${create_flags_array[@]}"; do cmd_str+=" '$flag'"; done
        echo "  Executing: $cmd_str"

        # Execute the create command
        issue_url=$(printf '%s' "$issue_body" | gh issue create -F - "${create_flags_array[@]}" ); create_exit_code=$?
        if [[ $create_exit_code -eq 0 ]]; then echo "  Issue created successfully: $issue_url";
        else echo >&2 "  Error creating issue '$TITLE' (Code: $create_exit_code)."; fi
    fi

    sleep 1
done

echo "----------------------------------------"; echo "GitHub Issue processing finished."; exit 0