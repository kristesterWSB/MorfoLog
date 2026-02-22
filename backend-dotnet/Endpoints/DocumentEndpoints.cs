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
using backend_dotnet.Services;

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

        group.MapPost("/upload", async (IFormFileCollection files, AppDbContext db, AiAnalysisService aiService, IWebHostEnvironment env, ClaimsPrincipal user) =>
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

            // Format DOB for AI context
            var dobFragment = dbUser.Profile.DateOfBirth.ToString("yyMMdd");

            foreach (var file in files)
            {
                var uniqueFileName = $"{Guid.NewGuid()}{Path.GetExtension(file.FileName)}";
                var absoluteFilePath = Path.Combine(uploadsDir, uniqueFileName);

                // Save file locally (optional now, but good for backup/download)
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
                db.Documents.Add(document); 

                // Send to AI Service
                var context = new Services.PatientContext(
                    dbUser.Profile.FirstName,
                    dbUser.Profile.LastName,
                    dobFragment,
                    dbUser.Profile.Address
                );

                try 
                {
                    using var fileStream = file.OpenReadStream();
                    var analysisResult = await aiService.AnalyzeDocumentAsync(fileStream, file.FileName, context);

                    if (analysisResult != null && analysisResult.Status == "success")
                    {
                        document.AnalysisJson = JsonSerializer.Serialize(analysisResult.Data);
                        document.Status = "Completed";
                    }
                    else
                    {
                        document.Status = "Error";
                    }
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Error processing file: {ex.Message}");
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