using backend_dotnet.Data;
using backend_dotnet.Endpoints;
using backend_dotnet.Models;
using Microsoft.EntityFrameworkCore;
using Microsoft.AspNetCore.Identity;
using Microsoft.OpenApi.Models;
using backend_dotnet.Services;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.
// Learn more about configuring OpenAPI at https://aka.ms/aspnet/openapi
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(c =>
{
    c.AddSecurityDefinition("Bearer", new OpenApiSecurityScheme
    {
        In = ParameterLocation.Header,
        Description = "Please enter into field the word 'Bearer' following by space and JWT",
        Name = "Authorization",
        Type = SecuritySchemeType.ApiKey
    });
    c.AddSecurityRequirement(new OpenApiSecurityRequirement
    {
        {
            new OpenApiSecurityScheme
            {
                Reference = new OpenApiReference
                {
                    Type = ReferenceType.SecurityScheme,
                    Id = "Bearer"
                }
            },
            new string[] {}
        }
    });
});

builder.Services.AddAuthorization();

builder.Services.AddIdentityApiEndpoints<User>()
    .AddEntityFrameworkStores<AppDbContext>();


// Register AppDbContext with PostgreSQL
var connectionString = Environment.GetEnvironmentVariable("DB_CONNECTION_STRING");
if (string.IsNullOrEmpty(connectionString))
{
    connectionString = builder.Configuration.GetConnectionString("DefaultConnection");
}

builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseNpgsql(connectionString));

// Register HttpClient for making requests to the Python service
builder.Services.AddHttpClient<AiAnalysisService>(client =>
{
    // Default to localhost for development, can be overridden by env var or appsettings
    var aiServiceUrl = builder.Configuration["AiServiceUrl"] ?? "http://localhost:8000";
    client.BaseAddress = new Uri(aiServiceUrl);
});

builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowReact", policy =>
    {
        // Allow localhost for development + origins from configuration (Cloud)
        var allowedOrigins = builder.Configuration.GetSection("AllowedCorsOrigins").Get<string[]>() ?? Array.Empty<string>();
        var origins = new List<string> { "http://localhost:5173" };
        origins.AddRange(allowedOrigins);

        policy.WithOrigins(origins.ToArray())
              .AllowAnyMethod()
              .AllowAnyHeader();
    });
});

var app = builder.Build();

using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
    db.Database.EnsureCreated();
}

// Configure the HTTP request pipeline.
app.UseSwagger();
app.UseSwaggerUI();

if (app.Environment.IsDevelopment())
{
    app.UseHttpsRedirection();
}

// Enable CORS
app.UseCors("AllowReact");

app.UseAuthentication();
app.UseAuthorization();

// Map document endpoints
app.MapAuthEndpoints();
app.MapProfileEndpoints();
app.MapGroup("/api/auth").MapIdentityApi<User>();
app.MapDocumentEndpoints();

app.Run();
