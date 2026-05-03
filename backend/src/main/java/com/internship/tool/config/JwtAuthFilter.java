package com.internship.tool.config;

import jakarta.servlet.*;
import jakarta.servlet.http.*;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.List;
import java.util.stream.Collectors;

@Component
public class JwtAuthFilter extends OncePerRequestFilter {

    private final JwtUtil jwtUtil;

    public JwtAuthFilter(JwtUtil jwtUtil) {
        this.jwtUtil = jwtUtil;
    }

    @Override
protected void doFilterInternal(HttpServletRequest request,
                                HttpServletResponse response,
                                FilterChain filterChain)
        throws ServletException, IOException {

    if (request.getServletPath().startsWith("/auth")) {
        filterChain.doFilter(request, response);
        return;
    }

    String header = request.getHeader("Authorization");
    System.out.println("🔐 Authorization header: " + header);

    if (header != null && header.startsWith("Bearer ")) {

        String token = header.substring(7);
        String username = jwtUtil.extractUsername(token);
        System.out.println("👤 Username from token: " + username);

        if (username != null && jwtUtil.validateToken(token)) {
            
            // Extract roles from token
            List<GrantedAuthority> authorities = List.of(
                new SimpleGrantedAuthority("ROLE_USER")
            );

            UsernamePasswordAuthenticationToken auth =
                new UsernamePasswordAuthenticationToken(
                    username,
                    null,
                    authorities
                );

            auth.setDetails(new WebAuthenticationDetailsSource().buildDetails(request));
            SecurityContextHolder.getContext().setAuthentication(auth);
            System.out.println("✅ Authentication set for user: " + username + " with authorities: " + authorities);
        } else {
            System.out.println("❌ Token validation failed");
        }
    } else {
        System.out.println("⚠️ No Bearer token found in header");
    }

    filterChain.doFilter(request, response);
}
}