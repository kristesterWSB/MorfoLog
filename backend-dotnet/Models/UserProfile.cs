using System;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace backend_dotnet.Models;

public class UserProfile
{
    [Key]
    [ForeignKey("User")]
    public Guid Id { get; set; }

    [Required]
    public string FirstName { get; set; } = null!;

    [Required]
    public string LastName { get; set; } = null!;

    [Required]
    public string Address { get; set; } = null!;

    [Required]
    public DateOnly DateOfBirth { get; set; }

    public virtual User User { get; set; } = null!;
}
