# Microservices with Automated CI/CD Pipeline Using GitLab

To address the limitations of monolithic architecture and manual deployment processes. The project involves decomposing a backend application into three independent microservices (Authentication, Products, Orders), containerizing them using Docker, and implementing a fully automated CI/CD pipeline with GitLab to streamline the entire build, test, and deployment lifecycle.

## Statement about the Problem
Traditional monolithic architectures are inherently rigid and difficult to scale, creating development shortcomings. When combined with manual, error-prone deployment processes, this leads to slow release cycles, inconsistent application environments, and an inability to deliver new features rapidly and reliably. 
This project directly confronts these inefficiencies by containerizing each microservice with Docker, managing the multi-service environment with Docker Compose, and creating a fully automated GitLab CI/CD pipeline to streamline the entire build and deployment process.

## Objectives:
-	Implement three microservices: (authentication, orders and product) using python Flask framework.
-	Containerize each microservice using Docker to ensure environment consistency.
-	Automate the deployment lifecycle by setting up a GitLab CI/CD pipeline to:
-	Build Docker images for each service on every push to GitLab Container Registry.
-	Automatically deploy the images to a remote server using Docker Compose.
 
## Scope:
-	Three microservices: Authentication Service, Orders microservice, Product Service microservice
-	The implementation is strictly backend-only.
-	The deployment orchestration is handled by Docker Compose.

## Project Structure

```
microservices-cicd/
├── auth_service/
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
├── products_service/
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
├── orders_service/
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
├── db_init/
│   └── init.sql
├── .gitignore
├── .gitlab-ci.yml 
└── docker-compose.yml
```

## Tech Stack

- Backend: Python (Flask Framework)
- Containerization: Docker & Docker Compose
- CI/CD: GitLab CI/CD
- Database: MySQL

## Getting Started: Local Setup
Follow these steps to get the project running on your local machine for development and testing.

### Prerequisites
Make sure you have the following software installed on your system:

- Git
- Docker
- Docker Compose

### Installation & Running
* **Clone the repository:**
     ```bash
        git clone <your-repository-url>
        cd microservices-cicd
        ```
* **Build and Run the Containers:**
    * Use Docker Compose to build the images and start all the services.
        ```bash
            docker-compose up --build
        ```
    * The `--build` flag forces a rebuild of the Docker images.
    * To run the containers in the background, use the `-d` (detached) flag:
        ```bash
        docker-compose up --build -d
        ```
* **Verify the Services:**
    * Check if all containers are running correctly.
        ```bash
        docker-compose ps
        ```
    * You can also view the logs for a specific service:
        ```bash
        docker-compose logs -f auth_service
        ```
    * The services should now be accessible on their respective ports as defined in `docker-compose.yml`.

## API Endpoints

### Authentication Service

| Method | Endpoint | Description |
| :----- | :----- | :----- |
| POST | `/register` | Register a new user. |
| POST | `/login` | Log in a user. |
| GET | `/logout` | Log out the current user. |
| GET | `/profile` | Get the current user's profile. |
| PUT | `/profile` | Update the user's profile. |

### Orders Service

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| POST | `/orders` | Create a new order. |
| GET | `/orders/user/:user_id` | Get all orders for a specific user. |
| PATCH | `/orders/:order_id/status` | Update the status of a specific order. |

### Product Service

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| GET | `/products` | Get a list of all products. |
| GET | `/products/:product_id` | Get details of a specific product. |
| GET | `/products/search?q={query}` | Search for products based on a query. |

## Conclusion

This is a final project made for the Job Value Added Course - DevOps Cloud training held in June - July 2025 by GLA University and Coding Blocks. 
