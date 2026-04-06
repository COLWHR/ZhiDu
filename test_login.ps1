$body = @{
    username = "testuser"
    password = "123456"
} | ConvertTo-Json

$response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/auth/login" -Method POST -Headers @{"Content-Type"="application/json"} -Body $body -UseBasicParsing

Write-Output "Status Code: $($response.StatusCode)"
Write-Output "Response: $($response.Content)"
