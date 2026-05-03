package com.internship.tool.controller;

import com.internship.tool.entity.Complaint;
import com.internship.tool.service.ComplaintService;

import jakarta.validation.Valid;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/complaints")
public class ComplaintController {

    private final ComplaintService service;

    public ComplaintController(ComplaintService service) {
        this.service = service;
    }

    // ✅ POST /create - Any authenticated user can create
    @PostMapping("/create")
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<Complaint> create(@Valid @RequestBody Complaint complaint) {
        System.out.println("📝 Creating complaint: " + complaint.getTitle());
        return new ResponseEntity<>(service.createComplaint(complaint), HttpStatus.CREATED);
    }

    // ✅ GET /all (pagination) - Any authenticated user can read
    @GetMapping("/all")
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<Page<Complaint>> getAll(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "5") int size) {

        System.out.println("📖 Fetching complaints page: " + page);
        return ResponseEntity.ok(service.getAllPaginated(PageRequest.of(page, size)));
    }

    // ✅ GET / (default - paginated) - Any authenticated user can read
    @GetMapping
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<Page<Complaint>> getAllDefault(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "5") int size) {

        return ResponseEntity.ok(service.getAllPaginated(PageRequest.of(page, size)));
    }

    // ✅ GET /{id} with 404 - Any authenticated user can read
    @GetMapping("/{id}")
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<Complaint> getById(@PathVariable Long id) {
        System.out.println("🔍 Fetching complaint: " + id);
        return ResponseEntity.ok(service.getById(id));
    }

    // ✅ PUT /{id} - Any authenticated user can update
    @PutMapping("/{id}")
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<Complaint> update(@PathVariable Long id, @Valid @RequestBody Complaint complaint) {
        System.out.println("✏️ Updating complaint: " + id);
        return ResponseEntity.ok(service.updateComplaint(id, complaint));
    }

    // ✅ DELETE /{id} - Any authenticated user can delete
    @DeleteMapping("/{id}")
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<Void> delete(@PathVariable Long id) {
        System.out.println("🗑️ Deleting complaint: " + id);
        service.deleteComplaint(id);
        return ResponseEntity.noContent().build();
    }
}