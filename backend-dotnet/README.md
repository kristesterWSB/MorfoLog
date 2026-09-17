# MorfoLog Backend (.NET)

This is the main API backend for the MorfoLog application, built with .NET 9.

## Overview

The backend acts as the central hub for the MorfoLog application. It exposes RESTful endpoints for the frontend, manages the PostgreSQL database, and proxies document processing tasks to the Python AI Engine. 

## Features
- **Document Management**: Endpoints for uploading, retrieving, and deleting medical documents.
- **AI Integration**: Communicates seamlessly with the `engine-python` microservice to extract structured data from uploaded PDFs or images.
- **Data Persistence**: Uses Entity Framework Core with PostgreSQL to store user profiles and medical result metadata.
- **Cloud-Ready**: Configured for Docker and deployment to Google Cloud Run with Cloud SQL integration.

## Prerequisites
- .NET 9 SDK
- PostgreSQL Server (Local or Docker)
- Running instance of the `engine-python` service (for local testing of document uploads)

## Getting Started

1. **Database Configuration**
   Update the connection string in `appsettings.Development.json`:
   ```json
   "ConnectionStrings": {
     "DefaultConnection": "Host=localhost;Database=morfolog_db;Username=postgres;Password=your_password"
   }
   ```

2. **AI Service Configuration**
   Ensure the `AiServiceUrl` points to your locally running Python engine (default is `http://localhost:8000` or `http://localhost:8088`):
   ```json
   "AiServiceUrl": "http://localhost:8000"
   ```

3. **Apply Database Migrations**
   Initialize the database schema using EF Core CLI:
   ```bash
   dotnet ef database update
   ```

4. **Run the API**
   Navigate to this directory and run the application:
   ```bash
   dotnet run
   ```
   By default, the API will run on `http://localhost:5180` (or the ports specified in `Properties/launchSettings.json`).

## Deployment
To deploy this service to Google Cloud Run, use the `deploy_backend.ps1` script located in the root of the repository. It will containerize the app using the provided `Dockerfile` and securely attach it to your Cloud SQL instance.
