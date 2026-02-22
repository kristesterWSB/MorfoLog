using System.Text.Json;
using System.Text.Json.Serialization;

namespace backend_dotnet.Services;

public class AiAnalysisService
{
    private readonly HttpClient _httpClient;
    private readonly ILogger<AiAnalysisService> _logger;

    public AiAnalysisService(HttpClient httpClient, ILogger<AiAnalysisService> logger)
    {
        _httpClient = httpClient;
        _logger = logger;
    }

    public async Task<AnalysisResult?> AnalyzeDocumentAsync(Stream fileStream, string fileName, PatientContext context)
    {
        try
        {
            using var content = new MultipartFormDataContent();
            
            // Add file content
            var fileContent = new StreamContent(fileStream);
            fileContent.Headers.ContentType = new System.Net.Http.Headers.MediaTypeHeaderValue("application/pdf");
            content.Add(fileContent, "file", fileName);

            // Add patient context as JSON string
            var jsonOptions = new JsonSerializerOptions 
            { 
                PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower 
            };
            var contextJson = JsonSerializer.Serialize(context, jsonOptions);
            content.Add(new StringContent(contextJson), "patient_context");

            // Send POST request
            var response = await _httpClient.PostAsync("/analyze", content);
            
            if (!response.IsSuccessStatusCode)
            {
                var errorContent = await response.Content.ReadAsStringAsync();
                _logger.LogError("AI Service error: {StatusCode} - {Content}", response.StatusCode, errorContent);
                return null;
            }

            var analysisResponse = await response.Content.ReadFromJsonAsync<AnalysisResponse>();
            
            // Return first result or null
            return analysisResponse?.Results?.FirstOrDefault();
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error communicating with AI service");
            return null;
        }
    }
}

// Support classes
public record PatientContext(
    string FirstName,
    string LastName,
    string DobFragment,
    string? Address
);

public record AnalysisResponse(
    [property: JsonPropertyName("results")] List<AnalysisResult> Results
);

public record AnalysisResult(
    [property: JsonPropertyName("file")] string File,
    [property: JsonPropertyName("status")] string Status,
    [property: JsonPropertyName("data")] JsonElement Data
);
