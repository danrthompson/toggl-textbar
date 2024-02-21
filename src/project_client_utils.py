import requests
import os
from base64 import b64encode

WORKSPACE_ID = 397836


def fetch_data(endpoint):
    api_key = os.environ.get("TOGGL_API_KEY")
    if not api_key:
        raise ValueError("No Toggl API key found.")

    url = f"https://api.track.toggl.com/api/v9/workspaces/{WORKSPACE_ID}/{endpoint}"
    auth = b64encode(f"{api_key}:api_token".encode("ascii")).decode("ascii")
    headers = {"Content-Type": "application/json", "Authorization": f"Basic {auth}"}

    response = requests.get(url, headers=headers)
    if not response.ok:
        raise ValueError(
            f"Error fetching {endpoint} from Toggl. Status code: {response.status_code}. Response: {response.text}"
        )

    return response.json()


def fetch_clients():
    return fetch_data("clients")


def fetch_projects():
    return fetch_data("projects")


def create_pid_list(projects: dict, client_ids: list[int]):
    return [project["id"] for project in projects if project["cid"] in client_ids]


def print_clients_and_projects(clients, projects):
    # Create a map of client ID to projects
    client_to_projects = {client["id"]: [] for client in clients}
    for project in projects:
        client_id = project.get("client_id")
        if client_id in client_to_projects:
            client_to_projects[client_id].append(project)

    # Print client names and IDs
    print("Clients:")
    for client in clients:
        print(f"{client['name']}: {client['id']}")

    # Print projects for each client
    print("\nProjects by Client:")
    for client in clients:
        print(f"\n{client['name']} (ID: {client['id']}) Projects:")
        for project in client_to_projects[client["id"]]:
            print(f"- {project['name']} (ID: {project['id']})")


if __name__ == "__main__":
    # Fetch projects and create the map
    clients = fetch_clients()
    projects = fetch_projects()
    print_clients_and_projects(clients, projects)
