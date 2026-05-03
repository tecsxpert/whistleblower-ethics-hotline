package com.internship.tool.controller;

import com.internship.tool.config.JwtUtil;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/auth")
public class AuthController {

    private final JwtUtil jwtUtil;

    public AuthController(JwtUtil jwtUtil) {
        this.jwtUtil = jwtUtil;
    }

    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("status", "✅ Backend is running!");
    }

    @PostMapping("/login")
    public Map<String, String> login(@RequestBody Map<String, String> user) {

        String username = user.get("username");
        String password = user.get("password");

        String token;
        
        System.out.println("🔓 Login attempt: " + username);
        
        // Admin login
        if ("admin".equals(username) && "admin123".equals(password)) {
            token = jwtUtil.generateAdminToken(username);
            System.out.println("✅ Admin login successful, token generated");
        }
        // Regular user login
        else if ("user".equals(username) && "user123".equals(password)) {
            token = jwtUtil.generateToken(username);
            System.out.println("✅ User login successful, token generated");
        }
        // Legacy test login
        else if ("admin".equals(username) && "1234".equals(password)) {
            token = jwtUtil.generateAdminToken(username);
            System.out.println("✅ Legacy admin login successful, token generated");
        }
        else {
            System.out.println("❌ Invalid credentials: " + username);
            throw new RuntimeException("Invalid credentials");
        }

        Map<String, String> response = new HashMap<>();
        response.put("token", token);
        response.put("username", username);
        System.out.println("📤 Token length: " + token.length());
        return response;
    }
}