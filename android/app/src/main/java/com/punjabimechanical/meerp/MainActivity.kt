package com.punjabimechanical.meerp

import android.content.Context
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.punjabimechanical.meerp.api.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import java.io.File

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { MeerpApp(applicationContext) }
    }
}

@Composable
fun MeerpApp(context: Context) {
    val scope = rememberCoroutineScope()
    var token by remember { mutableStateOf(context.getSharedPreferences("meerp", Context.MODE_PRIVATE).getString("token", null)) }
    var user by remember { mutableStateOf<UserDto?>(null) }
    var error by remember { mutableStateOf("") }
    var loading by remember { mutableStateOf(false) }

    LaunchedEffect(token) {
        if (token != null) {
            try { user = ApiClient.service.me("Token $token") }
            catch (_: Exception) { token = null; context.getSharedPreferences("meerp", Context.MODE_PRIVATE).edit().clear().apply() }
        }
    }

    if (token == null || user == null) {
        LoginScreen(loading, error) { username, password ->
            scope.launch {
                loading = true; error = ""
                try {
                    val response = ApiClient.service.login(LoginRequest(username.trim(), password))
                    token = response.token; user = response.user
                    context.getSharedPreferences("meerp", Context.MODE_PRIVATE).edit().putString("token", response.token).apply()
                } catch (e: Exception) { error = "Login failed. Check User ID/password and server connection." }
                finally { loading = false }
            }
        }
    } else {
        MainDashboard(context, token!!, user!!, onLogout = {
            token = null; user = null
            context.getSharedPreferences("meerp", Context.MODE_PRIVATE).edit().clear().apply()
        })
    }
}

@Composable
fun LoginScreen(loading: Boolean, error: String, onLogin: (String, String) -> Unit) {
    var username by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    Surface(Modifier.fillMaxSize()) {
        Column(Modifier.fillMaxSize().padding(28.dp), verticalArrangement = Arrangement.Center) {
            Text("ME-ERP", style = MaterialTheme.typography.headlineLarge)
            Text("Punjabi University Patiala • Mechanical Engineering", style = MaterialTheme.typography.titleMedium)
            Spacer(Modifier.height(24.dp))
            OutlinedTextField(username, { username = it }, label = { Text("University / User ID") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
            Spacer(Modifier.height(12.dp))
            OutlinedTextField(password, { password = it }, label = { Text("Password") }, modifier = Modifier.fillMaxWidth(), singleLine = true, visualTransformation = PasswordVisualTransformation(), keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password))
            Spacer(Modifier.height(16.dp))
            Button(enabled = !loading && username.isNotBlank() && password.isNotBlank(), onClick = { onLogin(username, password) }, modifier = Modifier.fillMaxWidth()) { Text(if (loading) "Signing in…" else "LOGIN") }
            if (error.isNotBlank()) { Spacer(Modifier.height(12.dp)); Text(error, color = MaterialTheme.colorScheme.error) }
        }
    }
}

@Composable
fun MainDashboard(context: Context, token: String, user: UserDto, onLogout: () -> Unit) {
    var tab by remember { mutableStateOf("HOME") }
    Column(Modifier.fillMaxSize()) {
        TopAppBar(title = { Text("ME-ERP • ${user.display_name ?: user.username}") })
        when (tab) {
            "HOME" -> HomeScreen(user)
            "APPLICATIONS" -> ApplicationsScreen(token, user)
            "NEW" -> NewApplicationScreen(token)
            "ANNOUNCEMENTS" -> AnnouncementsScreen(token)
            "IMPORT" -> ImportUsersScreen(context, token)
            "PROFILE" -> ProfileScreen(user)
        }
        Spacer(Modifier.weight(1f))
        NavigationBar {
            listOf("HOME" to "Home", "APPLICATIONS" to "Applications", "ANNOUNCEMENTS" to "Announcements", "PROFILE" to "Profile").forEach { (key, label) ->
                NavigationBarItem(selected = tab == key, onClick = { tab = key }, icon = {}, label = { Text(label) })
            }
        }
        if (user.role == "STUDENT") {
            Row(Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 4.dp)) { Button(onClick = { tab = "NEW" }, Modifier.fillMaxWidth()) { Text("+ New Application") } }
        }
        if (user.role == "STAFF" || user.role == "HOD" || user.role == "ADMIN") {
            Row(Modifier.fillMaxWidth().padding(12.dp)) { OutlinedButton(onClick = { tab = "IMPORT" }, Modifier.fillMaxWidth()) { Text("Office: Import Users CSV") } }
        }
        Row(Modifier.fillMaxWidth().padding(12.dp)) { OutlinedButton(onClick = onLogout, Modifier.fillMaxWidth()) { Text("LOG OUT") } }
    }
}

@Composable fun HomeScreen(user: UserDto) {
    Column(Modifier.fillMaxWidth().padding(20.dp)) {
        Text("Welcome", style = MaterialTheme.typography.titleLarge); Text(user.display_name ?: user.username, style = MaterialTheme.typography.headlineSmall)
        Spacer(Modifier.height(12.dp)); Text("Role: ${user.role}"); Text("Department: ${user.department ?: "Mechanical Engineering"}")
        user.employee_or_student_id?.let { Text("ID: $it") }; user.semester?.let { Text("Semester: $it") }; user.section?.let { Text("Section: $it") }
        Spacer(Modifier.height(20.dp)); Text("Use the navigation below to view applications and departmental announcements.")
    }
}

@Composable fun ApplicationsScreen(token: String, user: UserDto) {
    var data by remember { mutableStateOf<List<ApplicationDto>>(emptyList()) }; var error by remember { mutableStateOf("") }; val scope = rememberCoroutineScope()
    LaunchedEffect(Unit) { try { data = ApiClient.service.applications("Token $token") } catch (e: Exception) { error = "Could not load applications." } }
    Column(Modifier.fillMaxSize().padding(16.dp)) {
        Text(if (user.role == "STUDENT") "My Applications" else "Department Applications", style = MaterialTheme.typography.headlineSmall); if (error.isNotBlank()) Text(error, color = MaterialTheme.colorScheme.error)
        LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp)) { items(data) { a ->
            var processing by remember(a.id) { mutableStateOf(false) }
            Card(Modifier.fillMaxWidth()) { Column(Modifier.padding(16.dp)) {
                Text(a.application_id, style = MaterialTheme.typography.labelLarge); Text(a.subject, style = MaterialTheme.typography.titleMedium); Text("Status: ${a.status}")
                a.current_remark?.takeIf { it.isNotBlank() }?.let { Text("Remark: $it") }
                if (user.role != "STUDENT") {
                    Row(horizontalArrangement = Arrangement.spacedBy(6.dp), modifier = Modifier.padding(top = 8.dp)) {
                        listOf("APPROVE" to "Approve", "REJECT" to "Reject", "REVIEW" to "Review").forEach { (action, label) ->
                            OutlinedButton(enabled = !processing, onClick = { processing = true; scope.launch { try { ApiClient.service.processApplication("Token $token", a.id, ProcessRequest(action, "Processed from Android")); data = ApiClient.service.applications("Token $token") } catch (_: Exception) {} finally { processing = false } } }) { Text(label) }
                        }
                    }
                }
            } }
        } }
    }
}

@Composable fun NewApplicationScreen(token: String) {
    var types by remember { mutableStateOf<List<ApplicationTypeDto>>(emptyList()) }; var selected by remember { mutableStateOf<ApplicationTypeDto?>(null) }; var subject by remember { mutableStateOf("") }; var body by remember { mutableStateOf("") }; var message by remember { mutableStateOf("") }; var loading by remember { mutableStateOf(false) }; val scope = rememberCoroutineScope()
    LaunchedEffect(Unit) { try { types = ApiClient.service.applicationTypes("Token $token"); selected = types.firstOrNull() } catch (_: Exception) { message = "Could not load application types." } }
    Column(Modifier.fillMaxWidth().padding(16.dp)) {
        Text("New Application", style = MaterialTheme.typography.headlineSmall); Spacer(Modifier.height(12.dp))
        if (types.isNotEmpty()) { Text("Type: ${selected?.name ?: "Select"}"); Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) { types.take(4).forEach { t -> OutlinedButton(onClick = { selected = t }) { Text(t.name.take(12)) } } } }
        OutlinedTextField(subject, { subject = it }, label = { Text("Subject") }, Modifier.fillMaxWidth()); Spacer(Modifier.height(8.dp)); OutlinedTextField(body, { body = it }, label = { Text("Application details") }, Modifier.fillMaxWidth().height(160.dp))
        Spacer(Modifier.height(12.dp)); Button(enabled = !loading && selected != null && subject.isNotBlank() && body.isNotBlank(), onClick = { scope.launch { loading = true; message = ""; try { ApiClient.service.createApplication("Token $token", ApplicationCreate(selected!!.id, subject, body, null)); message = "Application submitted successfully."; subject = ""; body = "" } catch (_: Exception) { message = "Submission failed." }; loading = false } }, Modifier.fillMaxWidth()) { Text(if (loading) "Submitting…" else "SUBMIT APPLICATION") }
        if (message.isNotBlank()) Text(message, modifier = Modifier.padding(top = 12.dp))
    }
}

@Composable fun AnnouncementsScreen(token: String) {
    var data by remember { mutableStateOf<List<AnnouncementDto>>(emptyList()) }; LaunchedEffect(Unit) { try { data = ApiClient.service.announcements("Token $token") } catch (_: Exception) {} }
    LazyColumn(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) { item { Text("Announcements", style = MaterialTheme.typography.headlineSmall) }; items(data) { a -> Card(Modifier.fillMaxWidth()) { Column(Modifier.padding(16.dp)) { Text(a.title, style = MaterialTheme.typography.titleMedium); Text(a.body); Text("${a.audience} • ${a.published_at}", style = MaterialTheme.typography.labelSmall) } } } }
}

@Composable fun ProfileScreen(user: UserDto) { Column(Modifier.fillMaxWidth().padding(20.dp)) { Text("My Profile", style = MaterialTheme.typography.headlineSmall); Spacer(Modifier.height(12.dp)); Text("Name: ${user.display_name ?: user.username}"); Text("User ID: ${user.employee_or_student_id ?: user.username}"); Text("Role: ${user.role}"); Text("Email: ${user.email ?: "—"}"); Text("Phone: ${user.phone ?: "—"}"); Text("Department: ${user.department ?: "—"}") } }

@Composable fun ImportUsersScreen(context: Context, token: String) {
    var message by remember { mutableStateOf("") }; var busy by remember { mutableStateOf(false) }; val scope = rememberCoroutineScope()
    val launcher = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri: Uri? ->
        if (uri == null) return@rememberLauncherForActivityResult
        scope.launch {
            busy = true; message = "Uploading…"
            try {
                val file = withContext(Dispatchers.IO) {
                    val temp = File.createTempFile("users_", ".csv", context.cacheDir)
                    context.contentResolver.openInputStream(uri)!!.use { input -> temp.outputStream().use { output -> input.copyTo(output) } }; temp
                }
                val body = file.asRequestBody("text/csv".toMediaType()); val part = MultipartBody.Part.createFormData("file", "users.csv", body)
                val result = ApiClient.service.importUsers("Token $token", part)
                message = "Imported ${result.imported}: ${result.created} created, ${result.updated} updated. Errors: ${result.errors.size}."
                file.delete()
            } catch (e: Exception) { message = "Upload failed: ${e.message ?: "check API connection and permission"}" }
            finally { busy = false }
        }
    }
    Column(Modifier.fillMaxWidth().padding(20.dp)) { Text("Office User Import", style = MaterialTheme.typography.headlineSmall); Spacer(Modifier.height(8.dp)); Text("Upload the CSV supplied by the Mechanical Office. Required columns: username,password,role,name."); Spacer(Modifier.height(16.dp)); Button(enabled = !busy, onClick = { launcher.launch(arrayOf("text/csv", "text/comma-separated-values", "application/vnd.ms-excel")) }, Modifier.fillMaxWidth()) { Text(if (busy) "Uploading…" else "SELECT USER CSV") }; Spacer(Modifier.height(12.dp)); Text(message) }
}
