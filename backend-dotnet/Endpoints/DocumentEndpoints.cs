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
        var group = app.MapGroup("/api/documents");

        group.MapPost("/upload", async (IFormFileCollection files, AppDbContext db, IHttpClientFactory httpClientFactory, IWebHostEnvironment env) =>
        {
            if (files == null || files.Count == 0)
            {
                return Results.BadRequest("No files were uploaded.");
            }

            var uploadsDir = Path.GetFullPath(Path.Combine(env.ContentRootPath, "..", "uploads"));
            Directory.CreateDirectory(uploadsDir);

            var documents = new List<MedicalDocument>();
            var absoluteFilePaths = new List<string>();

            // Step A & B: Save each file and create a corresponding database record
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
                    UploadedAt = DateTime.UtcNow
                };
                documents.Add(document);
                absoluteFilePaths.Add(absoluteFilePath);
            }

            await db.Documents.AddRangeAsync(documents);
            await db.SaveChangesAsync();

            // Step C: Call the Python analysis service with a list of file paths
            var httpClient = httpClientFactory.CreateClient();
            var analysisServiceUrl = "http://localhost:8088/analyze";
            var normalizedPaths = absoluteFilePaths.Select(p => p.Replace('\\', '/')).ToList();

            try
            {
                var response = await httpClient.PostAsJsonAsync(analysisServiceUrl, new { file_paths = normalizedPaths });

                // Step D: Update database records based on the new response structure
                if (response.IsSuccessStatusCode)
                {
                    var analysisResponse = await response.Content.ReadFromJsonAsync<AnalysisResponse>();
                    if (analysisResponse?.Results != null)
                    {
                        // Match results using the unique, absolute file path as the key
                        var documentsByPath = documents.ToDictionary(doc => doc.FilePath.Replace('\\', '/'));

                        foreach (var result in analysisResponse.Results)
                        {
                            // Normalize the path from the Python response
                            var resultPath = result.File.Replace('\\', '/');

                            if (documentsByPath.TryGetValue(resultPath, out var docToUpdate))
                            {
                                if (result.Status == "success")
                                {
                                    // Serialize the "data" object back to a compact JSON string (no indentation)
                                    docToUpdate.AnalysisJson = JsonSerializer.Serialize(result.Data);
                                    docToUpdate.Status = "Completed";
                                }
                                else
                                {
                                    docToUpdate.Status = "Error";
                                }
                                documentsByPath.Remove(resultPath); // Mark as processed
                            }
                        }

                        // Any documents not found in the response are marked as errors
                        foreach (var docWithoutResult in documentsByPath.Values)
                        {
                            docWithoutResult.Status = "Error";
                        }
                    }
                }
                else
                {
                    foreach (var doc in documents) doc.Status = "Error";
                }
            }
            catch (HttpRequestException)
            {
                // Handle cases where the Python service is unavailable
                foreach(var doc in documents) doc.Status = "Error";
                await db.SaveChangesAsync(); // Save the error status
                return Results.Problem(
                    detail: "The analysis service is currently unavailable. The documents were saved, but could not be processed.",
                    statusCode: StatusCodes.Status503ServiceUnavailable,
                    title: "Analysis Service Unreachable"
                );
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

        group.MapGet("/", async (AppDbContext db) =>
        {
            var documents = await db.Documents.ToListAsync();
            
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
    }
}