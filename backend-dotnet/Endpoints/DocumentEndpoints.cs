using backend_dotnet.Data;
using backend_dotnet.Models;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Http;
using Microsoft.EntityFrameworkCore;
using System.Collections.Generic;
using System.IO;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;

namespace backend_dotnet.Endpoints;

// Helper classes to model the JSON response from the Python service
public record AnalysisResponse(
    [property: JsonPropertyName("results")] List<AnalysisResult> Results
);

public record AnalysisResult(
    [property: JsonPropertyName("file")] string File,
    [property: JsonPropertyName("status")] string Status,
    [property: JsonPropertyName("data")] JsonElement Data
);

// DTO for API responses to shape the output correctly
public record MedicalDocumentResponse(
    Guid Id,
    string FileName,
    string FilePath,
    string Status,
    JsonElement? AnalysisJson,
    DateTime UploadedAt
);


public static class DocumentEndpoints
{
    public static void MapDocumentEndpoints(this IEndpointRouteBuilder app)
    {
        var group = app.MapGroup("/api/documents").RequireAuthorization();

        group.MapPost("/upload", async (IFormFileCollection files, AppDbContext db, IHttpClientFactory httpClientFactory, IWebHostEnvironment env, ClaimsPrincipal user) =>
        {
            var userIdString = user.FindFirstValue(ClaimTypes.NameIdentifier);
            if (string.IsNullOrEmpty(userIdString) || !Guid.TryParse(userIdString, out var userId)) return Results.Unauthorized();

            // Load user with profile
            var dbUser = await db.Users.Include(u => u.Profile).FirstOrDefaultAsync(u => u.Id == userId);
            if (dbUser?.Profile == null)
            {
                return Results.Problem("User profile is incomplete.", statusCode: 400);
            }

            if (files == null || files.Count == 0)
            {
                return Results.BadRequest("No files were uploaded.");
            }

            var uploadsDir = Path.GetFullPath(Path.Combine(env.ContentRootPath, "..", "uploads"));
            Directory.CreateDirectory(uploadsDir);

            var documents = new List<MedicalDocument>();
            var httpClient = httpClientFactory.CreateClient();
            var analysisServiceUrl = "http://localhost:8088/analyze"; // Ensure this matches Python service port

            // Format DOB for AI context
            var dobFragment = dbUser.Profile.DateOfBirth.ToString("yyMMdd");

            foreach (var file in files)
            {
                var uniqueFileName = $"{Guid.NewGuid()}{Path.GetExtension(file.FileName)}";
                var absoluteFilePath = Path.Combine(uploadsDir, uniqueFileName);

                await using (var stream = new FileStream(absoluteFilePath, FileMode.Create))
                {
                    await file.CopyToAsync(stream);
                }

                var document = new MedicalDocument
                {
                    FileName = file.FileName,
                    FilePath = absoluteFilePath,
                    Status = "Pending",
                    UserId = userId,
                    UploadedAt = DateTime.UtcNow
                };
                
                documents.Add(document);
                db.Documents.Add(document); // Add to tracking immediately to get ID if needed, but we save later
                
                // Prepare payload for Python service
                var payload = new
                {
                    file_path = absoluteFilePath.Replace('\\', '/'),
                    patient_context = new
                    {
                        first_name = dbUser.Profile.FirstName,
                        last_name = dbUser.Profile.LastName,
                        dob_fragment = dobFragment,
                        address = dbUser.Profile.Address
                    }
                };

                try 
                {
                    var response = await httpClient.PostAsJsonAsync(analysisServiceUrl, payload);
                    
                    if (response.IsSuccessStatusCode)
                    {
                         // Assume Python service returns the analysis result directly or in a wrapper
                         // Adjust this based on Python service response structure.
                         // For now, assuming it returns the same structure but for single file? 
                         // Or maybe we can conform Python service to return { "status": "...", "data": ... }
                         
                         var analysisResponse = await response.Content.ReadFromJsonAsync<AnalysisResponse>();
                         // Handle response... logic simplifies here if we process per file
                         // But for now, let's just mark as uploaded and let a background worker process?
                         // The prompt implies synchronous processing ("Przygotuj obiekt... PostAsJsonAsync").
                         
                         if (analysisResponse?.Results != null && analysisResponse.Results.Count > 0)
                         {
                             var result = analysisResponse.Results.First(); // Assuming single result
                             if (result.Status == "success")
                             {
                                 document.AnalysisJson = JsonSerializer.Serialize(result.Data);
                                 document.Status = "Completed";
                             }
                             else
                             {
                                 document.Status = "Error";
                             }
                         }
                         else
                         {
                             document.Status = "Processed"; // Or some other status if parsing fails
                         }
                    }
                    else
                    {
                        document.Status = "Error";
                    }
                }
                catch
                {
                    document.Status = "Error";
                }
            }

            await db.SaveChangesAsync();

            // Map the database models to the response DTOs
            var responseDtos = documents.Select(doc => new MedicalDocumentResponse(
                doc.Id,
                doc.FileName,
                doc.FilePath,
                doc.Status,
                doc.AnalysisJson != null ? JsonDocument.Parse(doc.AnalysisJson).RootElement : null,
                doc.UploadedAt
            )).ToList();

            return Results.Ok(responseDtos);

        }).DisableAntiforgery();

        group.MapGet("/", async (AppDbContext db, ClaimsPrincipal user) =>
        {
            var userIdString = user.FindFirstValue(ClaimTypes.NameIdentifier);
            if (string.IsNullOrEmpty(userIdString) || !Guid.TryParse(userIdString, out var userId)) return Results.Unauthorized();

            var documents = await db.Documents.Where(d => d.UserId == userId).ToListAsync();
            
            // Map the database models to the response DTOs for consistent output
            var responseDtos = documents.Select(doc => new MedicalDocumentResponse(
                doc.Id,
                doc.FileName,
                doc.FilePath,
                doc.Status,
                doc.AnalysisJson != null ? JsonDocument.Parse(doc.AnalysisJson).RootElement : null,
                doc.UploadedAt
            )).ToList();

            return Results.Ok(responseDtos);
        });

        group.MapDelete("/{id}", async (Guid id, AppDbContext db, ClaimsPrincipal user) =>
        {
            var userIdString = user.FindFirstValue(ClaimTypes.NameIdentifier);
            if (string.IsNullOrEmpty(userIdString) || !Guid.TryParse(userIdString, out var userId)) return Results.Unauthorized();

            var document = await db.Documents.FirstOrDefaultAsync(d => d.Id == id && d.UserId == userId);
            
            if (document == null)
            {
                return Results.NotFound();
            }

            // Optional: Delete physical file if needed
            if (File.Exists(document.FilePath))
            {
                try 
                {
                    File.Delete(document.FilePath);
                }
                catch 
                { 
                    // Log error but continue with DB deletion
                }
            }

            db.Documents.Remove(document);
            await db.SaveChangesAsync();

            return Results.NoContent();
        });
    }
}