package mcp

import (
	"fmt"
	"strings"
)

func ApplyAdapter(adapter AdapterConfig, servers map[string]ServerConfig) (map[string]interface{}, error) {
	if adapter.Server == "" {
		return nil, fmt.Errorf("adapter for tool '%s' is missing 'server' field", adapter.Tool)
	}

	serverConfig, ok := servers[adapter.Server]
	if !ok {
		return nil, fmt.Errorf("adapter for tool '%s' targets unknown server '%s'", adapter.Tool, adapter.Server)
	}

	return substitute(adapter.Mapping, serverConfig).(map[string]interface{}), nil
}

func substitute(value interface{}, serverConfig ServerConfig) interface{} {
	switch v := value.(type) {
	case string:
		for key, val := range serverConfig {
			placeholder := fmt.Sprintf("{{%s}}", key)
			if strings.Contains(v, placeholder) {
				// If the value is exactly the placeholder, return the original value (preserving type)
				if v == placeholder {
					return val
				}
				// Otherwise, replace as string
				v = strings.ReplaceAll(v, placeholder, fmt.Sprintf("%v", val))
			}
		}
		return v
	case map[string]interface{}:
		result := make(map[string]interface{})
		for k, val := range v {
			result[k] = substitute(val, serverConfig)
		}
		return result
	case []interface{}:
		result := make([]interface{}, len(v))
		for i, val := range v {
			result[i] = substitute(val, serverConfig)
		}
		return result
	default:
		return v
	}
}
