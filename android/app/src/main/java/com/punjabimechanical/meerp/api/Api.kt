package com.punjabimechanical.meerp.api

import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.*

// Emulator: 10.0.2.2 reaches the Django server on the development PC.
// For a physical phone, replace this with your PC LAN IP or deployed HTTPS API URL.
private const val BASE_URL = "http://10.0.2.2:8000/api/"

data class LoginRequest(val username: String, val password: String)
data class LoginResponse(val token: String, val user: UserDto)
data class UserDto(
    val id: Int,
    val username: String,
    val first_name: String?,
    val last_name: String?,
    val email: String?,
    val role: String,
    val employee_or_student_id: String?,
    val phone: String?,
    val department: String?,
    val semester: Int?,
    val section: String?,
    val display_name: String?
)
data class ApplicationTypeDto(val id: Int, val name: String, val description: String?, val default_authority_role: String, val active: Boolean)
data class ApplicationDto(
    val id: Int, val application_id: String, val applicant_name: String?, val application_type: Int,
    val application_type_name: String?, val subject: String, val body: String, val authority: Int?,
    val status: String, val current_remark: String?, val attachment: String?, val created_at: String, val updated_at: String
)
data class AnnouncementDto(
    val id: Int, val title: String, val body: String, val audience: String, val attachment: String?,
    val published_by: Int, val published_by_name: String?, val published_at: String, val expires_at: String?, val active: Boolean
)
data class ApplicationCreate(val application_type: Int, val subject: String, val body: String, val authority: Int?)
data class ImportResult(val created: Int, val updated: Int, val errors: List<String>, val total_rows: Int, val imported: Int)
data class ProcessRequest(val action: String, val remark: String)

data class DashboardData(val user: UserDto, val announcements: List<AnnouncementDto>, val applications: List<ApplicationDto>)

interface MeerpApi {
    @POST("login/") suspend fun login(@Body request: LoginRequest): LoginResponse
    @GET("me/") suspend fun me(@Header("Authorization") token: String): UserDto
    @GET("announcements/") suspend fun announcements(@Header("Authorization") token: String): List<AnnouncementDto>
    @GET("applications/") suspend fun applications(@Header("Authorization") token: String): List<ApplicationDto>
    @GET("application-types/") suspend fun applicationTypes(@Header("Authorization") token: String): List<ApplicationTypeDto>
    @POST("applications/") suspend fun createApplication(@Header("Authorization") token: String, @Body body: ApplicationCreate): ApplicationDto
    @POST("applications/{id}/process/") suspend fun processApplication(@Header("Authorization") token: String, @Path("id") id: Int, @Body body: ProcessRequest): ApplicationDto
    @Multipart @POST("users/import/") suspend fun importUsers(@Header("Authorization") token: String, @Part file: MultipartBody.Part): ImportResult
}

object ApiClient {
    private val client = OkHttpClient.Builder().build()
    val service: MeerpApi by lazy {
        Retrofit.Builder().baseUrl(BASE_URL).client(client).addConverterFactory(GsonConverterFactory.create()).build().create(MeerpApi::class.java)
    }
}
