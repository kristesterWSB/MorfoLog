# Stage 1: Build (use SDK image)
# Updated to .NET 9.0
FROM mcr.microsoft.com/dotnet/sdk:9.0 AS build
WORKDIR /src

# Copy project file and restore dependencies (for better caching)
COPY ["backend-dotnet.csproj", "./"]
RUN dotnet restore "backend-dotnet.csproj"

# Copy remaining source code and publish
COPY . .
RUN dotnet publish "backend-dotnet.csproj" -c Release -o /app/publish

# Stage 2: Run (use lightweight Runtime image)
FROM mcr.microsoft.com/dotnet/aspnet:9.0
WORKDIR /app
COPY --from=build /app/publish .

# Expose port 8080 (standard for containerized .NET apps)
# This environment variable explicitly sets the listening port
ENV ASPNETCORE_HTTP_PORTS=8080
EXPOSE 8080

# The DLL name must match the project name
ENTRYPOINT ["dotnet", "backend-dotnet.dll"]
