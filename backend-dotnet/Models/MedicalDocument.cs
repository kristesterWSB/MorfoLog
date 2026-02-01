namespace backend_dotnet.Models;

public class MedicalDocument
{
    public Guid Id { get; init; } = Guid.NewGuid();
    public required string FileName { get; set; }
    public required string FilePath { get; set; }
    public required string Status { get; set; }
    public string? AnalysisJson { get; set; }
    public DateTime UploadedAt { get; set; } = DateTime.UtcNow;
}